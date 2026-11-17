"""Calibrate area reward bounds from sizing-extreme primitive areas."""
import json
from pathlib import Path
from . import config as cfg
from .gds_utils import compute_layout_area_um2
_REFERENCE = None

def get_area_reference_summary():
    return dict(_REFERENCE or {})

def get_area_reward_bounds():
    if _REFERENCE is None:
        raise RuntimeError('Area calibration is required before reward evaluation.')
    return _REFERENCE['area_reward_target_um2'], _REFERENCE['area_reward_max_um2']

def load_area_reference():
    global _REFERENCE
    _REFERENCE = json.loads((cfg.RESULTS_ROOT / 'area_reference.json').read_text())
    if _REFERENCE['topology'] != cfg.TOPOLOGY or _REFERENCE['metric_combo'] != cfg.METRIC_COMBO:
        raise ValueError('Area reference does not match the selected circuit and metrics.')
    return get_area_reference_summary()

def calibrate():
    from .sim_utils import get_step_dir, write_sp_for_ocelot, run_ocelot
    global _REFERENCE
    records = []
    for idx, extreme in enumerate(('min', 'max'), 1):
        sizing = {f'{g}.{p}': r[f'{p}_{extreme}'] for g,r in cfg.GROUP_RANGES.items() for p in ('l','w','nf')}
        folder = get_step_dir(-idx, 0) / cfg.LAYOUT_SUBCKT_NAME
        folder.mkdir(exist_ok=True)
        write_sp_for_ocelot(sizing, folder / f'{cfg.LAYOUT_SUBCKT_NAME}.sp')
        # Primitive geometry is usable even when downstream routing/verification fails.
        error = None
        try:
            run_ocelot(folder)
        except RuntimeError as exc:
            error = str(exc)
        candidates = [folder / name / 'devices' / cfg.LAYOUT_SUBCKT_NAME
                      for name in ('.ocelot', '.brahmastra')]
        candidates += [folder / 'primitives' / cfg.LAYOUT_SUBCKT_NAME]
        files = next((list(d.glob('*.gds')) for d in candidates if list(d.glob('*.gds'))), [])
        areas = {f.stem: compute_layout_area_um2(f) for f in files}
        if not areas or any(v is None or v <= 0 for v in areas.values()):
            raise RuntimeError(f'Calibration could not find valid primitive GDS areas in {folder}. {error or ""}')
        records.append({'sizing': sizing, 'primitive_areas_um2': areas, 'sum_um2': sum(areas.values())})
    records.sort(key=lambda x: x['sum_um2'])
    target = records[0]['sum_um2'] * (1 + cfg.AREA_TARGET_ROUTING_MARGIN_FRACTION)
    maximum = records[1]['sum_um2'] * (1 + cfg.AREA_MAX_MARGIN_FRACTION)
    if not 0 < target < maximum:
        raise ValueError(f'Invalid calibrated area bounds: {target}, {maximum}')
    _REFERENCE = {'topology': cfg.TOPOLOGY, 'metric_combo': cfg.METRIC_COMBO,
                  'source': 'sizing_extreme_primitive_sums', 'extremes': records,
                  'area_reward_target_um2': target, 'area_reward_max_um2': maximum}
    (cfg.RESULTS_ROOT / 'area_reference.json').write_text(json.dumps(_REFERENCE, indent=2))
    return get_area_reference_summary()
