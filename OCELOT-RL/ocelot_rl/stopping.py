import numpy as np
import torch

class EarlyStopController:

    def __init__(self, results_root, cfg):
        self.results_root = results_root
        self.cfg = cfg
        self.best_rolling = 0.0
        self.best_ep = 0
        self.best_path = results_root / 'best_weights.pt'
        self.degrade_count = 0
        self._loss_history = []
        self._loss_baseline = None
        self._alarm_count = 0
        self._alarm_cooldown = 0
        self.stop_training = False

    def on_loss(self, update_idx, loss_val, optimizer, log_fn):
        self._loss_history.append(loss_val)
        if self._alarm_cooldown > 0:
            self._alarm_cooldown -= 1
            return
        if self._loss_baseline is None:
            if len(self._loss_history) >= self.cfg['loss_alarm_window']:
                self._loss_baseline = float(np.mean(self._loss_history[:self.cfg['loss_alarm_window']]))
                print(f'  [LossAlarm] baseline set: {self._loss_baseline:.4f}')
            return
        alarm_ref = max(self._loss_baseline, 0.01)
        if loss_val > self.cfg['loss_alarm_factor'] * alarm_ref:
            self._alarm_count += 1
            self._alarm_cooldown = self.cfg['loss_alarm_cooldown']
            for g in optimizer.param_groups:
                g['lr'] *= self.cfg['loss_lr_reduction']
            lr_now = optimizer.param_groups[0]['lr']
            print(f"  [LossAlarm #{self._alarm_count}] loss={loss_val:.3f} > {self.cfg['loss_alarm_factor']:.0f}×{self._loss_baseline:.3f}. LR → {lr_now:.2e}")
            log_fn({'event': 'loss_alarm', 'alarm_count': self._alarm_count, 'loss': loss_val, 'lr': lr_now, 'baseline': self._loss_baseline})
            if self._alarm_count >= 3:
                print('[LossAlarm] 3 alarms fired — stopping training.')
                log_fn({'event': 'early_stop', 'reason': 'loss_alarm_runaway', 'alarm_count': self._alarm_count})
                self.stop_training = True

    def on_batch_end(self, n_done, episode_success, q_net, log_fn):
        if self.stop_training:
            return True
        if n_done < self.cfg['window']:
            return False
        window = episode_success[-self.cfg['window']:]
        roll = sum(window) / self.cfg['window']
        if roll > self.best_rolling:
            self.best_rolling = roll
            self.best_ep = n_done
            torch.save(q_net.state_dict(), self.best_path)
            print(f'  [BestCkpt] new best {roll:.3f} at ep {n_done} → {self.best_path}')
            log_fn({'event': 'best_checkpoint', 'episode': n_done, 'rolling': float(roll)})
        if roll >= self.cfg['target']:
            print(f"[EarlyStop] Target {roll:.3f} ≥ {self.cfg['target']:.3f} at ep {n_done}.")
            log_fn({'event': 'early_stop', 'episode': n_done, 'rate': float(roll), 'reason': 'target'})
            return True
        if roll < self.best_rolling - self.cfg['degrade_thresh']:
            self.degrade_count += 1
        else:
            self.degrade_count = 0
        if self.degrade_count >= self.cfg['degrade_patience']:
            print(f'[EarlyStop] Degradation: rolling={roll:.3f}, best={self.best_rolling:.3f} (ep {self.best_ep}), stale for {self.degrade_count} eps. Restoring weights.')
            log_fn({'event': 'early_stop', 'episode': n_done, 'rate': float(roll), 'reason': 'degradation', 'best_ep': self.best_ep, 'best_rolling': float(self.best_rolling)})
            if self.best_path.exists():
                q_net.load_state_dict(torch.load(self.best_path, weights_only=True))
            return True
        return False
