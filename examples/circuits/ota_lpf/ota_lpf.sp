.subckt ota_lpf GND VDD VINN VINP VBIAS VOUT
    * First Stage - Differential Pair with Current Mirror Load
    M0 tail VBIAS GND  GND sky130_fd_pr__nfet_01v8 l=0.15e-6 w=6e-6   nf=2
    M1 net1 VINN  tail GND sky130_fd_pr__nfet_01v8 l=0.15e-6 w=15e-6  nf=2
    M2 net2 VINP  tail GND sky130_fd_pr__nfet_01v8 l=0.15e-6 w=15e-6  nf=2
    M3 net1 net1  VDD  VDD sky130_fd_pr__pfet_01v8 l=0.15e-6 w=12e-6  nf=2
    M4 net2 net1  VDD  VDD sky130_fd_pr__pfet_01v8 l=0.15e-6 w=12e-6  nf=2
 
    * Second Stage - Common Source Amplifier
    M5 VOUT net2 VDD VDD sky130_fd_pr__pfet_01v8 l=0.15e-6 w=30e-6  nf=2
    M6 VOUT net2 GND GND sky130_fd_pr__nfet_01v8 l=0.15e-6 w=15e-6  nf=2
 
    * Miller Compensation with Nulling Resistor
    C0 net2 VOUT sky130_fd_pr__cap_mim_m3_2 l=21e-6 w=21e-6
    XR0 net2 net2_int GND sky130_fd_pr__res_xhigh_po r=20k
 
    * Load Capacitance
    C1 VOUT GND sky130_fd_pr__cap_mim_m3_2 l=5e-6 w=5e-6
 
    * Bias Circuit
    M7 VBIAS VBIAS GND GND sky130_fd_pr__nfet_01v8 l=0.15e-6 w=3e-6 nf=2
 
    * RC Low-Pass filter moved inside the OTA subcircuit
    XR1 VINN VOUT GND sky130_fd_pr__res_xhigh_po r=20k
    C2 VINN  VOUT     sky130_fd_pr__cap_mim_m3_2 l=40e-6 w=40e-6
.ends ota_lpf