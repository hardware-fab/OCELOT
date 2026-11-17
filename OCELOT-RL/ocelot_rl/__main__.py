"""Command-line entry point for cold-start training and final evaluation."""
import argparse
import os
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='examples/miller_ota_B.yaml')
    parser.add_argument('--mode', choices=('check', 'full', 'train', 'test'), default='full')
    args = parser.parse_args()
    os.environ['OCELOT_RL_CONFIG'] = args.config
    from . import config as cfg
    for path in (cfg.LAYOUT_EXECUTABLE, cfg.DRC_FILE, cfg.PDK_ROOT / 'libs.tech/ngspice/sky130.lib.spice'):
        if not path.is_file():
            parser.error(f'Required file is missing: {path}. Configure settings.yaml first.')
    if not os.access(cfg.LAYOUT_EXECUTABLE, os.X_OK):
        parser.error(f'Layout executable is not executable: {cfg.LAYOUT_EXECUTABLE}')
    for command in ('ngspice', 'magic', 'netgen'):
        if shutil.which(command) is None:
            parser.error(f'Required command is not on PATH: {command}')
    for key in ('episodes', 'horizon', 'parallel_episodes', 'checkpoint_interval', 'batch_size',
                'replay_capacity', 'train_every', 'updates_per_event', 'lr_decay_episodes', 'epsilon_decay_episodes'):
        if int(cfg.TRAIN[key]) <= 0:
            parser.error(f'training.{key} must be positive')
    if int(cfg.SETTINGS['evaluation']['episodes']) <= 0:
        parser.error('evaluation.episodes must be positive')
    from .train import train
    from .evaluate import evaluate
    print(f'OCELOT-RL: {cfg.TOPOLOGY} / {cfg.METRIC_COMBO}; output: {cfg.RESULTS_ROOT}')
    if args.mode == 'check':
        print('Configuration, Python imports and tool paths checked; no simulations executed.')
        return
    starts = train() if args.mode in ('train', 'full') else None
    if args.mode in ('test', 'full'):
        evaluate(starts)


if __name__ == '__main__':
    main()
