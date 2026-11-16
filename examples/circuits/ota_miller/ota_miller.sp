.subckt ota_miller VINP VINM VBIAS VDD GND VOUTP VOUTM
    
    M1  net1  VINP  net3 GND sky130_fd_pr__nfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M2  net2  VINM  net3 GND sky130_fd_pr__nfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M5  net3  VBIAS GND  GND sky130_fd_pr__nfet_01v8    l=1e-6    w=4e-6   nf=2
    M3  net1  net4  VDD  VDD sky130_fd_pr__pfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M4  net2  net4  VDD  VDD sky130_fd_pr__pfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M6  VOUTP net1  VDD  VDD sky130_fd_pr__pfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M8  VOUTP VBIAS GND  GND sky130_fd_pr__nfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M7  VOUTM net2  VDD  VDD sky130_fd_pr__pfet_01v8    l=0.2e-6  w=2e-6   nf=2
    M9  VOUTM VBIAS GND  GND sky130_fd_pr__nfet_01v8    l=0.2e-6  w=2e-6   nf=2

    C0  net2   netrc0          sky130_fd_pr__cap_mim_m3_1 l=20e-6  w=20e-6
    XR0 netrc0 VOUTM  GND      sky130_fd_pr__res_xhigh_po_5p73 r=10k
    C1  net1   netrc1          sky130_fd_pr__cap_mim_m3_1 l=20e-6  w=20e-6
    XR1 netrc1 VOUTP  GND      sky130_fd_pr__res_xhigh_po_5p73 r=10k

.ends ota_miller
