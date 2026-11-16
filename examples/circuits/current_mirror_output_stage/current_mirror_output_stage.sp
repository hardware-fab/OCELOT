.subckt current_mirror_output_stage VINM VINP VDD GND VCTRL
    MN3     net1  net1  net2 GND sky130_fd_pr__nfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MN4     net3  net1  net2 GND sky130_fd_pr__nfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MN1     net4  VINM  net3 GND sky130_fd_pr__nfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MN2     net5  VINP  net3 GND sky130_fd_pr__nfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MN5     VCTRL VCTRL GND  GND sky130_fd_pr__nfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2

    MP1     net4  net4  VDD  VDD sky130_fd_pr__pfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MP2     net5  net4  VDD  VDD sky130_fd_pr__pfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2
    MP3     VCTRL net5  VDD  VDD sky130_fd_pr__pfet_01v8_lvt      l=0.5e-6 w=2.5e-6 nf=2 

    XRBIAS0 VDD   netr0 GND      sky130_fd_pr__res_xhigh_po r=5k
    XRBIAS1 netr0 netr1 GND      sky130_fd_pr__res_xhigh_po r=5k
    XRBIAS2 netr1 netr2 GND      sky130_fd_pr__res_xhigh_po r=5k
    XRBIAS3 netr2 net1  GND      sky130_fd_pr__res_xhigh_po r=5k
.ends current_mirror_output_stage