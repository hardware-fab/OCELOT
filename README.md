# OCELOT

This repository contains the implementation accompanying the paper **“OCELOT: Analog Electronic Design Automation through RL-based Layout Design and Optimization”**, currently under review at *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*.

## Setup

Install the following dependencies using the instructions provided in their official repositories:

- [SkyWater SKY130 PDK](https://github.com/google/skywater-pdk)
- [Magic](https://github.com/rtimothyedwards/magic), version 8.3.637
- [Netgen](https://github.com/rtimothyedwards/netgen), version 1.5.300
- [Ngspice](https://ngspice.sourceforge.io/index.html), version 43

## Usage

Set the `PDK_ROOT` environment variable to the path of your PDK installation, such as `/usr/local/share/pdk/sky130A`, then run OCELOT with the desired circuit and PDK configuration:

```bash
export PDK_ROOT=/usr/local/share/pdk/sky130A
./OCELOT ./examples/circuits/<circuit-name> ./examples/drc_info/skywater_130.json
```

Replace `<circuit-name>` with the name of the circuit you want to process.

## Cold-start reinforcement learning

The [OCELOT-RL setup and execution guide](OCELOT-RL/OCELOT-RL_GUIDE.md) describes the cold-start Double-DQN package, local tool configuration, area calibration, and the Miller OTA-B example using CMRR and PSRR.

## Authors

- **Giuseppe Chiari** — [giuseppe.chiari@polimi.it](mailto:giuseppe.chiari@polimi.it)
- **Michele Piccoli** — [michele.piccoli@polimi.it](mailto:michele.piccoli@polimi.it)
- **Davide Zoni** — [davide.zoni@polimi.it](mailto:davide.zoni@polimi.it)
