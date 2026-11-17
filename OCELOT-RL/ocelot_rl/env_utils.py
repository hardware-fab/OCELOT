import random
import math
import json
import time
import numpy as np
from .config import MATCHING_GROUPS, BRANCHES, ACTION_DIM, STATE_DIM, GROUP_RANGES, REWARD_METRICS, AREA_OBS_MAX
from .simulate import simulate_and_get_metrics
from .sim_utils import write_step_netlist, get_step_dir, write_json
from .area_reference import get_area_reference_summary

def read_step_sim_timing(step_dir):
    timing_path = step_dir / 'sim_timing.json'
    if not timing_path.exists():
        return {}
    try:
        return json.loads(timing_path.read_text())
    except Exception:
        return {}
ACTIONS = []
for group in MATCHING_GROUPS:
    r = GROUP_RANGES[group]
    ACTIONS.extend([(group, 'l', +r['l_step']), (group, 'l', -r['l_step']), (group, 'w', +r['w_step']), (group, 'w', -r['w_step']), (group, 'nf', +r['nf_step']), (group, 'nf', -r['nf_step'])])
assert len(ACTIONS) == ACTION_DIM, f'ACTIONS length {len(ACTIONS)} != ACTION_DIM {ACTION_DIM}'

def action_to_dict(idx):
    group, param, delta = ACTIONS[idx]
    return {'action_idx': int(idx), 'group': group, 'param': param, 'delta': float(delta), 'op': 'increase' if delta > 0 else 'decrease'}

def _snap(value, lo, hi, step):
    if lo is None or hi is None or step is None:
        raise ValueError(f'Invalid grid bounds: lo={lo}, hi={hi}, step={step}')
    n = round((float(value) - float(lo)) / float(step))
    n = int(np.clip(n, 0, round((float(hi) - float(lo)) / float(step))))
    return round(float(lo) + n * float(step), 4)

def apply_action(sizing, action_idx):
    group, param, delta = ACTIONS[action_idx]
    key = f'{group}.{param}'
    new_sizing = dict(sizing)
    r = GROUP_RANGES[group]
    if param == 'l':
        new_sizing[key] = _snap(sizing[key] + delta, r['l_min'], r['l_max'], r['l_step'])
    elif param == 'w':
        new_sizing[key] = _snap(sizing[key] + delta, r['w_min'], r['w_max'], r['w_step'])
    elif param == 'nf':
        new_sizing[key] = int(np.clip(int(sizing[key]) + int(delta), r['nf_min'], r['nf_max']))
    return new_sizing

def build_grid(lo, hi, step):
    n = int(round((hi - lo) / step))
    grid = [round(lo + i * step, 4) for i in range(n + 1)]
    grid[-1] = round(hi, 4)
    return grid

def sample_random_config(rng=random):
    cfg = {}
    for group in MATCHING_GROUPS:
        r = GROUP_RANGES[group]
        l_grid = build_grid(r['l_min'], r['l_max'], r['l_step'])
        w_grid = build_grid(r['w_min'], r['w_max'], r['w_step'])
        nf_grid = list(range(r['nf_min'], r['nf_max'] + 1, r['nf_step']))
        cfg[f'{group}.l'] = float(rng.choice(l_grid))
        cfg[f'{group}.w'] = float(rng.choice(w_grid))
        cfg[f'{group}.nf'] = int(rng.choice(nf_grid))
    return cfg

def build_state_vector(sizing, metrics=None, layout_area_um2=None):
    sizing_slots = []
    for group, members in MATCHING_GROUPS.items():
        r = GROUP_RANGES[group]
        lr = max(r['l_max'] - r['l_min'], 1e-09)
        wr = max(r['w_max'] - r['w_min'], 1e-09)
        nfr = max(r['nf_max'] - r['nf_min'], 1)
        l_val = sizing.get(f'{group}.l')
        w_val = sizing.get(f'{group}.w')
        nf_val = sizing.get(f'{group}.nf')
        if l_val is None or w_val is None or nf_val is None:
            raise ValueError(f'Missing sizing values for group {group}: l={l_val}, w={w_val}, nf={nf_val}')
        for _ in members:
            sizing_slots += [(float(l_val) - r['l_min']) / lr, (float(w_val) - r['w_min']) / wr, (int(nf_val) - r['nf_min']) / nfr]
    metric_vals = []
    if metrics is not None:
        for spec in REWARD_METRICS:
            raw = metrics.get(spec['key'])
            val = float(raw) if raw is not None else spec['fallback']
            lo, hi = (spec['obs_min'], spec['obs_max'])
            val = max(lo, min(hi, val))
            if spec['log_scale']:
                span = math.log10(hi) - math.log10(lo)
                norm = (math.log10(val) - math.log10(lo)) / span if span > 1e-12 else 0.0
            else:
                span = hi - lo
                norm = (val - lo) / span if span > 1e-09 else 0.0
            metric_vals.append(float(np.clip(norm, 0.0, 1.0)))
        area_um2 = float(layout_area_um2 or 0.0)
        area_norm = float(np.clip(area_um2 / max(AREA_OBS_MAX, 1e-09), 0.0, 1.0))
        metric_vals.append(area_norm)
    else:
        for spec in REWARD_METRICS:
            metric_vals.append(0.0 if spec['direction'] == 'floor' else 1.0)
        metric_vals.append(1.0)
    n_transistors = sum((len(v) for v in MATCHING_GROUPS.values()))
    metric_slots = metric_vals * n_transistors
    state = sizing_slots + metric_slots
    assert len(state) == STATE_DIM, f'build_state_vector: length {len(state)} != STATE_DIM {STATE_DIM}'
    return np.array(state, dtype=np.float32)

def get_valid_action_indices(sizing):
    valid = []
    for idx, (group, param, delta) in enumerate(ACTIONS):
        r = GROUP_RANGES[group]
        key = f'{group}.{param}'
        if param == 'l':
            curr = float(sizing[key])
            new_v = _snap(curr + delta, r['l_min'], r['l_max'], r['l_step'])
            if not np.isclose(new_v, curr):
                valid.append(idx)
        elif param == 'w':
            curr = float(sizing[key])
            new_v = _snap(curr + delta, r['w_min'], r['w_max'], r['w_step'])
            if not np.isclose(new_v, curr):
                valid.append(idx)
        elif param == 'nf':
            curr = int(sizing[key])
            new_v = int(np.clip(curr + int(delta), r['nf_min'], r['nf_max']))
            if new_v != curr:
                valid.append(idx)
    return valid

def evaluate_sizing_config(sizing, episode_idx, step_idx, action_idx=None, action_label=None, sizing_before=None):
    step_t0 = time.perf_counter()
    from .reward import compute_reward
    metrics, layout_area_um2 = simulate_and_get_metrics(sizing=sizing, corner='tt', temp=27, episode_idx=episode_idx, step_idx=step_idx)
    step_dir = get_step_dir(episode_idx, step_idx)
    write_step_netlist(sizing, step_dir)
    sim_timing = read_step_sim_timing(step_dir)
    area_reference = get_area_reference_summary()
    if metrics is None:
        reward, done, errors = (0.0, False, {br: 999.0 for br in BRANCHES})
        timed_out = bool(sim_timing.get('timed_out', False))
        fail_state = build_state_vector(sizing)
        overall_step_time_s = round(time.perf_counter() - step_t0, 6)
        write_json(step_dir / 'step_meta.json', {'episode': int(episode_idx), 'step': int(step_idx), 'action_idx': int(action_idx) if action_idx is not None else None, 'action': action_label, 'sizing_before': sizing_before, 'sizing_after': sizing, 'reward': 0.0, 'done': False, 'branch_errors': errors, 'all_failed': True, 'timed_out': timed_out, 'timing': sim_timing, 'ocelot_time_s': sim_timing.get('ocelot_time_s'), 'ngspice_time_s': sim_timing.get('ngspice_time_s'), 'overall_step_time_s': overall_step_time_s, 'area_reference': area_reference})
        return (fail_state, 0.0, False, {'branch_errors': errors, 'all_failed': True, 'timed_out': timed_out, 'timing': sim_timing, 'overall_step_time_s': overall_step_time_s, 'area_reference': area_reference})
    reward, done, errors = compute_reward(metrics, layout_area_um2)
    next_state = build_state_vector(sizing, metrics, layout_area_um2)
    metric_log = {spec['key']: float(metrics.get(spec['key'], 0.0) or 0.0) for spec in REWARD_METRICS}
    metric_log['area_um2'] = float(layout_area_um2 or 0.0)
    overall_step_time_s = round(time.perf_counter() - step_t0, 6)
    write_json(step_dir / 'step_meta.json', {'episode': int(episode_idx), 'step': int(step_idx), 'action_idx': int(action_idx) if action_idx is not None else None, 'action': action_label, 'sizing_before': sizing_before, 'sizing_after': sizing, 'reward': float(reward), 'done': bool(done), 'branch_errors': errors, 'timing': sim_timing, 'ocelot_time_s': sim_timing.get('ocelot_time_s'), 'ngspice_time_s': sim_timing.get('ngspice_time_s'), 'overall_step_time_s': overall_step_time_s, 'area_reference': area_reference, **metric_log})
    return (next_state, reward, done, {'branch_errors': errors, 'done': bool(done), 'timing': sim_timing, 'overall_step_time_s': overall_step_time_s, 'area_reference': area_reference, **metric_log})

def env_step(sizing, action_idx, episode_idx, step_idx):
    new_sizing = apply_action(sizing, action_idx)
    action_group, action_param, action_delta = ACTIONS[action_idx]
    action_label = {'group': action_group, 'param': action_param, 'delta': float(action_delta)}
    next_state, reward, done, info = evaluate_sizing_config(sizing=new_sizing, episode_idx=episode_idx, step_idx=step_idx, action_idx=action_idx, action_label=action_label, sizing_before=sizing)
    return (new_sizing, next_state, reward, done, info)
