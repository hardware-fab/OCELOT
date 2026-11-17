"""Cold-start DDQN training with parallel online episode collection."""
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import numpy as np
import torch
from tqdm import tqdm
from . import config as cfg
from .model import QNetwork, ReplayBuffer, RewardNormalizer, select_action_masked, dqn_train_step, polyak_update
from .env_utils import sample_random_config, evaluate_sizing_config, env_step
from .sim_utils import write_json, get_episode_dir
from .area_reference import calibrate
from .stopping import EarlyStopController

def sizing_key(sizing):
    return tuple(sorted(sizing.items()))

def collect_episode(episode, weights, epsilon, seed, sizing, evaluation=False):
    rng = random.Random(seed)
    net = QNetwork(cfg.STATE_DIM, cfg.ACTION_DIM).to(cfg.DEVICE)
    net.load_state_dict(weights)
    net.eval()
    write_json(get_episode_dir(episode) / 'episode_meta.json',
               {'episode': episode, 'initial_sizing': sizing, 'epsilon': epsilon})
    state, _, initially_done, info = evaluate_sizing_config(sizing, episode, 0)
    transitions = []
    # Evaluation accepts a starting sizing which already meets every done band.
    done = bool(initially_done) if evaluation else False
    for step in range(1, int(cfg.TRAIN['horizon']) + 1):
        if done:
            break
        action, _ = select_action_masked(net, state, sizing, epsilon, cfg.ACTION_DIM, rng)
        sizing, next_state, reward, done, info = env_step(sizing, action, episode, step)
        transitions.append((state, action, reward, next_state, float(done)))
        state = next_state
    result = {'episode': episode, 'steps': len(transitions), 'success': bool(done),
              'initial_success': bool(initially_done), 'final_sizing': sizing,
              'total_reward': sum(t[2] for t in transitions), 'final_info': info}
    write_json(get_episode_dir(episode) / 'episode_result.json', result)
    return result, transitions

def contract():
    return {'topology': cfg.TOPOLOGY, 'metric_combo': cfg.METRIC_COMBO,
            'matching_groups': cfg.MATCHING_GROUPS, 'group_ranges': cfg.GROUP_RANGES,
            'reward_metrics': cfg.REWARD_METRICS, 'hidden_layers': list(cfg.Q_HIDDEN_LAYERS)}

def train():
    cfg.RESULTS_ROOT.mkdir(parents=True, exist_ok=False)
    write_json(cfg.RESULTS_ROOT / 'run_config.json', cfg.SETTINGS)
    random.seed(cfg.SEED); np.random.seed(cfg.SEED); torch.manual_seed(cfg.SEED)
    calibrate()
    net = QNetwork(cfg.STATE_DIM, cfg.ACTION_DIM).to(cfg.DEVICE)
    target = QNetwork(cfg.STATE_DIM, cfg.ACTION_DIM).to(cfg.DEVICE)
    target.load_state_dict(net.state_dict())
    optimizer = torch.optim.Adam(net.parameters(), lr=float(cfg.TRAIN['lr_start']))
    replay = ReplayBuffer(int(cfg.TRAIN['replay_capacity']))
    normalizer = RewardNormalizer()
    stop = EarlyStopController(cfg.RESULTS_ROOT, cfg.TRAIN['early_stop'])
    success = []; steps = updates = completed = 0
    started = time.perf_counter(); training_starts = set()
    events = cfg.RESULTS_ROOT / 'training_events.jsonl'
    def log(event):
        with events.open('a') as f: f.write(json.dumps(event) + '\n')
    def snapshot():
        return {k:v.detach().cpu().clone() for k,v in net.state_dict().items()}
    def save(name):
        torch.save({'q_net_state_dict': snapshot(), 'contract': contract(),
                    'episodes_trained': completed, 'global_step': steps}, cfg.RESULTS_ROOT / name)
    def submit(pool, ep):
        frac = min(ep / int(cfg.TRAIN['epsilon_decay_episodes']), 1.0)
        eps = float(cfg.TRAIN['epsilon_start']) + frac * (float(cfg.TRAIN['epsilon_end']) - float(cfg.TRAIN['epsilon_start']))
        lr = float(cfg.TRAIN['lr_end']) + (float(cfg.TRAIN['lr_start']) - float(cfg.TRAIN['lr_end'])) * max(0, 1-ep/int(cfg.TRAIN['lr_decay_episodes']))
        for g in optimizer.param_groups: g['lr'] = min(g['lr'], lr)
        sizing = sample_random_config(random.Random(cfg.SEED + ep))
        training_starts.add(sizing_key(sizing))
        return pool.submit(collect_episode, ep, snapshot(), eps, cfg.SEED + ep, sizing)
    budget = int(cfg.TRAIN['episodes']); workers = int(cfg.TRAIN['parallel_episodes'])
    stopping = False; next_ep = 1
    with ThreadPoolExecutor(max_workers=workers) as pool, tqdm(total=budget, desc='Training', unit='episode') as bar:
        pending = {}
        while next_ep <= min(workers, budget):
            pending[submit(pool, next_ep)] = next_ep; next_ep += 1
        while pending:
            ready, _ = wait(pending, return_when=FIRST_COMPLETED)
            for f in ready:
                ep = pending.pop(f)
                # Unexpected implementation/setup errors surface; tool failures are logged by the evaluator.
                result, transitions = f.result()
                completed += 1; success.append(result['success'])
                for transition in transitions:
                    replay.add(*transition); steps += 1
                    if steps > int(cfg.TRAIN['learning_starts']) and steps % int(cfg.TRAIN['train_every']) == 0:
                        for _ in range(int(cfg.TRAIN['updates_per_event'])):
                            loss = dqn_train_step(net, target, optimizer, replay, int(cfg.TRAIN['batch_size']),
                                                  float(cfg.TRAIN['gamma']), normalizer,
                                                  float(cfg.TRAIN['entropy_coefficient']))
                            if loss is None: break
                            polyak_update(net, target); updates += 1
                            stop.on_loss(updates, loss, optimizer, log)
                log({'event':'episode_summary', 'episode':ep, 'steps':result['steps'], 'success':result['success']})
                stopping = stopping or stop.on_batch_end(completed, success, net, log)
                if completed % int(cfg.TRAIN['checkpoint_interval']) == 0:
                    save(f'checkpoint_{completed:05d}.pt')
                bar.update(); bar.set_postfix(success=f'{sum(success)/completed:.3f}')
                if not stopping and next_ep <= budget:
                    pending[submit(pool, next_ep)] = next_ep; next_ep += 1
    save('q_net.pt')
    write_json(cfg.RESULTS_ROOT/'train_summary.json', {'episodes_trained':completed, 'global_steps':steps,
               'optimizer_updates':updates, 'success_rate':sum(success)/completed,
               'elapsed_s':time.perf_counter()-started})
    return training_starts
