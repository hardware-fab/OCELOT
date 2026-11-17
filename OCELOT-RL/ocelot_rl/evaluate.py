"""Evaluate the final DDQN policy with online sampling of fresh starting sizings."""
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import torch
from tqdm import tqdm
from . import config as cfg
from .area_reference import load_area_reference
from .env_utils import sample_random_config
from .sim_utils import write_json
from .train import collect_episode, contract, sizing_key

def evaluate(training_starts=None):
    checkpoint = torch.load(cfg.RESULTS_ROOT / 'q_net.pt', map_location='cpu', weights_only=True)
    if checkpoint['contract'] != contract():
        raise ValueError('The model circuit, metrics or sizing grid differ from the selected configuration.')
    load_area_reference()
    output = cfg.RESULTS_ROOT / 'evaluation'
    output.mkdir(exist_ok=False)
    reserved = set(training_starts or ())
    if training_starts is None:
        for p in cfg.RESULTS_ROOT.glob('episode_*/episode_meta.json'):
            d=json.loads(p.read_text())
            if d['episode']>0: reserved.add(sizing_key(d['initial_sizing']))
    rng = random.Random(int(cfg.SETTINGS['evaluation']['seed']))
    count = int(cfg.SETTINGS['evaluation']['episodes'])
    # Episode storage helpers use sim_utils.RESULTS_ROOT; calibration was loaded above.
    from . import sim_utils
    sim_utils.RESULTS_ROOT = output
    results=[]
    with ThreadPoolExecutor(max_workers=int(cfg.TRAIN['parallel_episodes'])) as pool:
        pending=[]
        for i in range(1, count+1):
            for _ in range(100000):
                sizing=sample_random_config(rng)
                if sizing_key(sizing) not in reserved: break
            else: raise ValueError('Cannot sample a fresh test start; requested count may exhaust the sizing grid.')
            reserved.add(sizing_key(sizing))
            pending.append(pool.submit(collect_episode, i, checkpoint['q_net_state_dict'], 0.0,
                                       int(cfg.SETTINGS['evaluation']['seed'])+i, sizing, True))
        for f in tqdm(as_completed(pending), total=count, desc='Evaluation', unit='episode'):
            result,_=f.result(); results.append(result)
    results.sort(key=lambda x:x['episode'])
    write_json(output/'summary.json',{'episodes':count,'successes':sum(r['success'] for r in results),
                                     'success_rate':sum(r['success'] for r in results)/count,
                                     'cases':results})
