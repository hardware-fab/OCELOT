import math
from .config import BRANCHES, BRANCH_WEIGHTS, REWARD_METRICS, REWARD_BONUS, REWARD_TAU_AREA_UM2
from .area_reference import get_area_reward_bounds

def compute_reward(metrics, layout_area_um2):
    if metrics is None:
        errors = {br: 999.0 for br in BRANCHES}
        return (0.0, False, errors)
    area_um2 = float(layout_area_um2 or 0.0)
    branch_rewards = {}
    branch_errors = {}
    branch_norm_errs = {}
    all_done = True
    for spec in REWARD_METRICS:
        raw = metrics.get(spec['key'])
        br = spec['key']
        if raw is None and br == 'pm_deg':
            dc_gain = metrics.get('dc_gain_dB')
            if dc_gain is not None and float(dc_gain) < 0:
                val = 180.0 + abs(float(dc_gain))
            else:
                val = spec['fallback']
        else:
            val = float(raw) if raw is not None else spec['fallback']
        tau = spec['tau']
        direction = spec['direction']
        is_log = spec.get('log_scale', False)
        if direction == 'band':
            done_ok = spec['done_bound_lo'] <= val <= spec['done_bound_hi']
            if is_log:
                lo = math.log10(max(spec['target_lo'], 1e-09))
                hi = math.log10(max(spec['target_hi'], 1e-09))
                log_val = math.log10(max(val, 1e-09))
                log_tau = 1.0
                err_log = max(0.0, log_val - hi) + max(0.0, lo - log_val)
                r = math.exp(-err_log / log_tau)
                err = max(0.0, val - spec['target_hi']) + max(0.0, spec['target_lo'] - val)
                norm_err = err_log / log_tau
            else:
                err = max(0.0, val - spec['target_hi']) + max(0.0, spec['target_lo'] - val)
                r = math.exp(-err / tau)
                norm_err = err / max(tau, 1e-09)
        elif direction == 'ceiling':
            done_ok = val <= spec['done_bound']
            if is_log:
                target_log = math.log10(max(spec['target'], 1e-09))
                log_val = math.log10(max(val, 1e-09))
                log_tau = 1.0
                err_log = max(0.0, log_val - target_log)
                r = math.exp(-err_log / log_tau)
                err = max(0.0, val - spec['target'])
                norm_err = err_log / log_tau
            else:
                err = max(0.0, val - spec['target'])
                r = math.exp(-err / tau)
                norm_err = err / max(tau, 1e-09)
        else:
            done_ok = val >= spec['done_bound']
            if is_log:
                target_log = math.log10(max(spec['target'], 1e-09))
                log_val = math.log10(max(val, 1e-09))
                log_tau = 1.0
                err_log = max(0.0, target_log - log_val)
                r = math.exp(-err_log / log_tau)
                err = max(0.0, spec['target'] - val)
                norm_err = err_log / log_tau
            else:
                err = max(0.0, spec['target'] - val)
                r = math.exp(-err / tau)
                norm_err = err / max(tau, 1e-09)
        branch_rewards[br] = r
        branch_errors[br] = err
        branch_norm_errs[br] = norm_err
        all_done = all_done and done_ok
    if area_um2 <= 0.0:
        R_area = 0.5
        norm_err_area = 0.0
    else:
        area_reward_target_um2, area_reward_max_um2 = get_area_reward_bounds()
        if area_um2 <= area_reward_target_um2:
            R_area = 1.0
            norm_err_area = 0.0
        elif area_um2 >= area_reward_max_um2:
            R_area = 0.0
            norm_err_area = (area_um2 - area_reward_target_um2) / max(REWARD_TAU_AREA_UM2, 1e-09)
        else:
            R_area = 1.0 - (area_um2 - area_reward_target_um2) / (area_reward_max_um2 - area_reward_target_um2)
            norm_err_area = (area_um2 - area_reward_target_um2) / max(REWARD_TAU_AREA_UM2, 1e-09)
    branch_errors['area'] = area_um2 / max(REWARD_TAU_AREA_UM2, 1e-09)
    branch_norm_errs['area'] = norm_err_area
    alpha = 1.0
    total_w = 0.0
    reward = 0.0
    for br in branch_rewards:
        eff_w = BRANCH_WEIGHTS[br] * (1.0 + alpha * branch_norm_errs[br])
        total_w += eff_w
        reward += eff_w * branch_rewards[br]
    area_eff_w = BRANCH_WEIGHTS['area'] * (1.0 + alpha * branch_norm_errs['area'])
    total_w += area_eff_w
    reward += area_eff_w * R_area
    reward /= total_w
    if all_done:
        reward += float(REWARD_BONUS)
    return (float(reward), all_done, branch_errors)
