# OCELOT

This repository contains the implementation accompanying the paper **“OCELOT: Analog Electronic Design Automation through RL-based Layout Design and Optimization”**, awaiting for approval in the *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*.

# Usage

Install the SkyWater SKY130 PDK by following the instructions in the [official repository](https://github.com/google/skywater-pdk).

Set the `PDK_ROOT` environment variable to the path of your PDK installation, such as `/usr/local/share/pdk/sky130A`, then run OCELOT with the desired circuit and PDK configuration:

```bash
export PDK_ROOT=/usr/local/share/pdk/sky130A
./ocelot-linux-x86_64/OCELOT ./examples/circuits/<circuit-name> ./examples/pdks/skywater_130.json
```

Replace `<circuit-name>` with the name of the circuit you want to process.

## Authors

- **Giuseppe Chiari** — [giuseppe.chiari@polimi.it](mailto:giuseppe.chiari@polimi.it)
- **Michele Piccoli** — [michele.piccoli@polimi.it](mailto:michele.piccoli@polimi.it)
- **Davide Zoni** — [davide.zoni@polimi.it](mailto:davide.zoni@polimi.it)
