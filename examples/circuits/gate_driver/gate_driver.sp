.subckt gate_driver VDD GND VIN VOUT

    M1  n1 VIN    VDD VDD  sky130_fd_pr__pfet_01v8 w=10e-6 l=1e-6 nf=1 
    M2  n1 VIN    GND GND  sky130_fd_pr__nfet_01v8 w=5e-6  l=1e-6 nf=1 

    XRLS1 n1      nls1 GND sky130_fd_pr__res_xhigh_po r=200k
    XRLS2 n1      nls2 GND sky130_fd_pr__res_xhigh_po r=200k

    M3  nls1 n1   VDD VDD sky130_fd_pr__pfet_01v8 w=20e-6 l=1e-6 nf=1
    M4  nls2 n1   GND GND sky130_fd_pr__nfet_01v8 w=10e-6 l=1e-6 nf=1
    M7  VOUT n1   VDD VDD sky130_fd_pr__pfet_01v8 w=20e-6 l=1e-6 nf=1
    M8  VOUT n1   GND GND sky130_fd_pr__nfet_01v8 w=20e-6 l=1e-6 nf=1

    M5  gout VOUT VDD VDD  sky130_fd_pr__pfet_01v8 w=50e-6 l=1e-6 nf=1
    M6  gout VOUT GND GND  sky130_fd_pr__nfet_01v8 w=50e-6 l=1e-6 nf=1

.ends gate_driver
