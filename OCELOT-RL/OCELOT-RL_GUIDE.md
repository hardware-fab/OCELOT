# OCELOT-RL

## Setup

Use Python 3.10 or newer on Linux. Install the dependencies listed in the parent README, plus ngspice and an open_pdks SKY130A installation. Ensure `magic`, `netgen`, and `ngspice` are on `PATH`.

From the `OCELOT-RL` directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp settings.example.yaml settings.yaml
```

In `settings.yaml`, set `pdk_root` to your SKY130A directory (containing `libs.tech`). Keep `ocelot_root: ..` when using the enclosing OCELOT repository; otherwise set it to the directory containing the OCELOT executable and its supporting files.

## Usage

Edit `examples/miller_ota_B.yaml` to set `training.parallel_episodes` and a new, non-existing `output_dir`. Relative paths are resolved against the YAML file containing them.

```bash
# Check configuration and tool paths
python -m ocelot_rl --config examples/miller_ota_B.yaml --mode check

# Run area calibration, training, and testing
python -m ocelot_rl --config examples/miller_ota_B.yaml
```

Use `--mode train` or `--mode test` to run the phases separately. Testing loads the saved model and requires a non-existing `evaluation` subdirectory.

## Outputs

Files are saved under `output_dir` (default: `results/miller_ota_B`):

| File or directory | Contents |
| --- | --- |
| `run_config.json` | Experiment configuration |
| `area_reference.json` | Calibrated area reward bounds |
| `episode_*/` | Per-step netlists, layouts, simulation logs, and episode summaries |
| `checkpoint_*.pt` | Periodic model checkpoints |
| `q_net.pt` | Final trained model |
| `train_summary.json` | Training success rate, steps, and runtime |
| `evaluation/` | Test trajectories and aggregate results in `summary.json` |
