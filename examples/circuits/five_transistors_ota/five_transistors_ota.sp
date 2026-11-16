.subckt five_transistors_ota VSS VDD VOUT VINN VINP VBIAS
    M0 source VBIAS GND GND sky130_fd_pr__nfet_01v8 l=5.000e-07 w=3.100e-06 nf=2
    M1 VOUT VINN source GND sky130_fd_pr__nfet_01v8 l=5.000e-07 w=3.100e-06 nf=2
    M2 net8 VINP source GND sky130_fd_pr__nfet_01v8 l=2.750e-07 w=3.100e-06 nf=3
    M3 VOUT net8 VDD VDD sky130_fd_pr__pfet_01v8    l=475.000e-9 w=3.500e-06 nf=2
    M4 net8 net8 VDD VDD sky130_fd_pr__pfet_01v8    l=5.000e-07 w=3.000e-06 nf=2
.ends five_transistors_ota