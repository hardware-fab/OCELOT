.subckt ota_hpf GND VDD VOUT VINN VINP VBIAS VFILTER
    M0  tail    VBIAS    GND  GND  sky130_fd_pr__nfet_01v8    w=6e-6  l=150e-9 nf=1
    M1  net1    VINN     tail GND  sky130_fd_pr__nfet_01v8    w=15e-6 l=150e-9 nf=1
    M2  net2    VINP     tail GND  sky130_fd_pr__nfet_01v8    w=15e-6 l=150e-9 nf=1
    M3  net1    net1     VDD  VDD  sky130_fd_pr__pfet_01v8    w=12e-6 l=150e-9 nf=1
    M4  net2    net1     VDD  VDD  sky130_fd_pr__pfet_01v8    w=12e-6 l=150e-9 nf=1
    M5  VOUT    net2     VDD  VDD  sky130_fd_pr__pfet_01v8    w=30e-6 l=150e-9 nf=1
    M6  VOUT    net2     GND  GND  sky130_fd_pr__nfet_01v8    w=15e-6 l=150e-9 nf=1
    C0  net2_int    VOUT           sky130_fd_pr__cap_mim_m3_2 l=21e-6 w=21e-6
    XR0 net2    net2_int GND       sky130_fd_pr__res_xhigh_po r=10k
    C1  VOUT    GND                sky130_fd_pr__cap_mim_m3_2 l=5e-6  w=5e-6
    M7  VBIAS   VBIAS    GND  GND  sky130_fd_pr__nfet_01v8    w=3e-6  l=150e-9 nf=1
    C2  VOUT    VFILTER            sky130_fd_pr__cap_mim_m3_2 l=90e-6 w=90e-6
    XR1 VFILTER GND      GND       sky130_fd_pr__res_xhigh_po r=18k
.ends ota_hpf