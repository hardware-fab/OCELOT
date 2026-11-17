import math
import random
import numpy as np
import torch
import torch.nn as nn
from collections import deque
from .config import DEVICE, ACTION_DIM, STATE_DIM, POLYAK_TAU, Q_HIDDEN_LAYERS
from .env_utils import get_valid_action_indices

class QNetwork(nn.Module):

    def __init__(self, state_dim, action_dim):
        super().__init__()
        layers = []
        input_dim = state_dim
        for hidden_dim in Q_HIDDEN_LAYERS:
            layers.extend((nn.Linear(input_dim, hidden_dim), nn.ReLU()))
            input_dim = hidden_dim
        layers.append(nn.Linear(input_dim, action_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

class ReplayBuffer:

    def __init__(self, capacity=50000):
        self.buffer = deque(maxlen=capacity)

    def add(self, s, a, r, ns, d):
        self.buffer.append((s, a, r, ns, d))

    def sample(self, batch_size=64):
        batch = random.sample(self.buffer, batch_size)
        s, a, r, ns, d = zip(*batch)
        return (np.array(s, dtype=np.float32), np.array(a, dtype=np.int64), np.array(r, dtype=np.float32), np.array(ns, dtype=np.float32), np.array(d, dtype=np.float32))

    def __len__(self):
        return len(self.buffer)

class RewardNormalizer:

    def __init__(self, alpha: float=0.001):
        self.mean = 0.0
        self.var = 1.0
        self.alpha = alpha

    def update_and_normalize(self, rewards_np: np.ndarray) -> np.ndarray:
        batch_mean = float(rewards_np.mean())
        batch_var = float(rewards_np.var())
        self.mean = (1.0 - self.alpha) * self.mean + self.alpha * batch_mean
        self.var = (1.0 - self.alpha) * self.var + self.alpha * max(batch_var, 1e-06)
        std = max(math.sqrt(self.var), 1e-06)
        return (rewards_np - self.mean) / std

def polyak_update(q_net: nn.Module, target_net: nn.Module, tau: float=POLYAK_TAU) -> None:
    with torch.no_grad():
        for param, target_param in zip(q_net.parameters(), target_net.parameters()):
            target_param.data.mul_(1.0 - tau)
            target_param.data.add_(tau * param.data)

def dqn_train_step(q_net, target_net, optimizer, replay, batch_size=64, gamma=0.99, reward_normalizer=None, entropy_coeff=0.0):
    if len(replay) < batch_size:
        return None
    s, a, r, ns, d = replay.sample(batch_size)
    if reward_normalizer is not None:
        r = reward_normalizer.update_and_normalize(r)
    s_t = torch.tensor(s, dtype=torch.float32, device=DEVICE)
    a_t = torch.tensor(a, dtype=torch.int64, device=DEVICE).unsqueeze(1)
    r_t = torch.tensor(r, dtype=torch.float32, device=DEVICE).unsqueeze(1)
    ns_t = torch.tensor(ns, dtype=torch.float32, device=DEVICE)
    d_t = torch.tensor(d, dtype=torch.float32, device=DEVICE).unsqueeze(1)
    q_all = q_net(s_t)
    q_pred = q_all.gather(1, a_t)
    with torch.no_grad():
        best_actions = q_net(ns_t).argmax(dim=1, keepdim=True)
        q_next = target_net(ns_t).gather(1, best_actions)
        q_target = r_t + gamma * (1.0 - d_t) * q_next
    loss = nn.functional.smooth_l1_loss(q_pred, q_target)
    if entropy_coeff > 0.0:
        probs = torch.softmax(q_all, dim=-1)
        entropy = -(probs * torch.log(probs + 1e-08)).sum(dim=-1).mean()
        loss = loss - entropy_coeff * entropy
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(q_net.parameters(), max_norm=0.5)
    optimizer.step()
    return float(loss.item())

def select_action_masked(q_net, state, sizing, epsilon, action_dim, rng=random):
    valid = get_valid_action_indices(sizing)
    if not valid:
        return (rng.randrange(action_dim), 0)
    if rng.random() < epsilon:
        return (rng.choice(valid), len(valid))
    with torch.no_grad():
        s_t = torch.tensor(state, dtype=torch.float32, device=DEVICE).unsqueeze(0)
        q_vals = q_net(s_t).squeeze(0).cpu().numpy()
    masked = np.full(action_dim, -np.inf, dtype=np.float32)
    for idx in valid:
        masked[idx] = q_vals[idx]
    return (int(np.argmax(masked)), len(valid))
