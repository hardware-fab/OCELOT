"""Evaluate a sizing through OCELOT layout generation and extracted SPICE."""
import math
import threading
import time
from . import config as cfg
from .sim_utils import (get_step_dir, write_sp_for_ocelot, run_ocelot,
                        build_postlayout_testbench, run_ngspice_deck, parse_metrics_txt,
                        OCELOTFailure, write_json)
from .gds_utils import compute_layout_area_um2
_CACHE = {}
_LOCK = threading.Lock()

def simulate_and_get_metrics(sizing, corner='tt', temp=27, episode_idx=0, step_idx=0):
    key = (tuple(sorted(sizing.items())), corner, temp)
    step_dir = get_step_dir(episode_idx, step_idx)
    start = time.perf_counter()
    with _LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        metrics, area, original = cached
        write_json(step_dir / 'sim_timing.json', {'cache_hit': True, 'original_sim_dir': original,
                   'simulation_time_s': time.perf_counter() - start})
        return metrics, area
    folder = step_dir / cfg.LAYOUT_SUBCKT_NAME
    folder.mkdir(exist_ok=True)
    write_sp_for_ocelot(sizing, folder / f'{cfg.LAYOUT_SUBCKT_NAME}.sp')
    timing = {'cache_hit': False}
    try:
        t = time.perf_counter()
        run_ocelot(folder)
        timing['ocelot_time_s'] = time.perf_counter() - t
        gds = folder / f'{cfg.LAYOUT_SUBCKT_NAME}.gds'
        area = compute_layout_area_um2(gds)
        extracted = folder / 'gds-extracted.spice'
        if not extracted.is_file() or area is None:
            raise OCELOTFailure(f'Missing extracted netlist or layout geometry in {folder}')
        metrics_path = step_dir / 'metrics.txt'
        deck = step_dir / 'postlayout.sp'
        deck.write_text(build_postlayout_testbench(extracted.read_text(), corner, temp, metrics_path))
        t = time.perf_counter()
        run_ngspice_deck(deck)
        timing['ngspice_time_s'] = time.perf_counter() - t
        if not metrics_path.is_file():
            raise RuntimeError(f'ngspice did not write {metrics_path}')
        metrics = parse_metrics_txt(metrics_path)
        if not metrics or any(metrics.get(s['key']) is None or not math.isfinite(metrics[s['key']]) for s in cfg.REWARD_METRICS):
            raise RuntimeError(f'Missing selected metrics in {metrics_path}')
    except (OCELOTFailure, RuntimeError) as exc:
        metrics, area = None, None
        timing['error'] = str(exc)
    timing['simulation_time_s'] = time.perf_counter() - start
    write_json(step_dir / 'sim_timing.json', timing)
    if metrics is not None:
        with _LOCK:
            _CACHE[key] = (metrics, area, str(step_dir))
    return metrics, area
