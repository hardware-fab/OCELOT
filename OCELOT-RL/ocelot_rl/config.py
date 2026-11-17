"""Configuration shared by the cold-start trainer and circuit evaluator."""
import importlib
import json
import os
import subprocess
import threading
from pathlib import Path
import torch
import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get('OCELOT_RL_CONFIG', PACKAGE_ROOT / 'examples/miller_ota_B.yaml')).resolve()
SETTINGS = yaml.safe_load(CONFIG_PATH.read_text())

def path_value(value, base):
    p = Path(value).expanduser()
    return (base / p).resolve() if not p.is_absolute() else p.resolve()

LOCAL_PATH = path_value(SETTINGS.get('local_settings', '../settings.yaml'), CONFIG_PATH.parent)
LOCAL = yaml.safe_load(LOCAL_PATH.read_text()) if LOCAL_PATH.exists() else {}
OCELOT_ROOT = path_value(LOCAL.get('ocelot_root', '..'), LOCAL_PATH.parent)
LAYOUT_EXECUTABLE = OCELOT_ROOT / 'OCELOT'
DRC_FILE = OCELOT_ROOT / 'examples/drc_info/skywater_130.json'
PDK_ROOT = path_value(LOCAL.get('pdk_root', '/path/to/sky130A'), LOCAL_PATH.parent)
PDK_LIB_PATH = str(PDK_ROOT / 'libs.tech/ngspice/sky130.lib.spice')
RESULTS_ROOT = path_value(SETTINGS.get('output_dir', '../results/miller_ota_B'), CONFIG_PATH.parent)
TOPOLOGY = SETTINGS.get('topology', 'miller_ota')
METRIC_COMBO = SETTINGS.get('metric_combo', 'OTA-B')
if TOPOLOGY not in ('five_transistors', 'miller_ota', 'ahuja_ota', 'hpf', 'lpf'):
    raise ValueError(f'Unsupported topology: {TOPOLOGY}')
topo_module = importlib.import_module(f'.topologies.{TOPOLOGY}', package='ocelot_rl')
for name in ('TEMPLATE','MATCHING_GROUPS','REFERENCE_SIZING','LAYOUT_SUBCKT_NAME','REWARD_BONUS','REWARD_TAU_AREA_UM2','AREA_OBS_MAX'):
    globals()[name] = getattr(topo_module, name)
REWARD_METRICS = topo_module.METRIC_PRESETS[METRIC_COMBO]
GROUP_RANGES = {g: {f'{p}_{k}': getattr(topo_module, f'{p.upper()}_{k.upper()}_{g}')
                   for p in ('l','w','nf') for k in ('min','max','step')} for g in MATCHING_GROUPS}
BRANCHES = [s['key'] for s in REWARD_METRICS] + ['area']
BRANCH_WEIGHTS = {s['key']: s['weight'] for s in REWARD_METRICS}
BRANCH_WEIGHTS['area'] = 1.0
STATE_DIM = sum(len(v) for v in MATCHING_GROUPS.values()) * (3 + len(REWARD_METRICS) + 1)
ACTION_DIM = len(MATCHING_GROUPS) * 6
TRAIN = SETTINGS['training']
SEED = int(TRAIN['seed'])
Q_HIDDEN_LAYERS = (256, 256)
POLYAK_TAU = 0.005
DEVICE = torch.device(LOCAL.get('device', 'cpu'))
torch.set_num_threads(int(LOCAL.get('torch_threads', 2)))
NGSPICE_SEM = threading.Semaphore(int(LOCAL.get('ngspice_processes', 3)))
CORNER_VDD_MAP = {'tt': 'v180'}
VDD_VOLTS = {'v180': 1.8}
AREA_TARGET_ROUTING_MARGIN_FRACTION = float(SETTINGS['area']['target_margin'])
AREA_MAX_MARGIN_FRACTION = float(SETTINGS['area']['maximum_margin'])
