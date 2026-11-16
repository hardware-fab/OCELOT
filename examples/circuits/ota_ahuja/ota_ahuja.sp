.subckt ota_ahuja INM GND VDD OUT
    M7  net1  out1  GND   GND sky130_fd_pr__nfet_01v8_lvt l=220e-9   w=4e-6     nf=2
    M10 vbias vbias GND   GND sky130_fd_pr__nfet_01v8_lvt l=180e-9   w=5.6e-6   nf=2
    M11 vcas  vcas  vbias GND sky130_fd_pr__nfet_01v8_lvt l=180e-9   w=5.6e-6   nf=2
    M9  net1  vbias GND   GND sky130_fd_pr__nfet_01v8_lvt l=220e-9   w=4e-6     nf=1
    M6  OUT   net1  GND   GND sky130_fd_pr__nfet_01v8_lvt l=220e-9   w=5.5e-6   nf=1
    M13 out1  vcas  net7  GND sky130_fd_pr__nfet_01v8_lvt l=3.6e-6   w=16.0e-6  nf=2
    M12 net18 vcas  net16 GND sky130_fd_pr__nfet_01v8_lvt l=3.6e-6   w=16.0e-6  nf=2
    M0  net16 INM   net11 GND sky130_fd_pr__nfet_01v8_lvt l=360e-9   w=10e-6    nf=1
    M2  OUT   net1  GND   GND sky130_fd_pr__nfet_01v8_lvt l=360e-9   w=10e-6    nf=4
    M1  net11 vbias GND   GND sky130_fd_pr__nfet_01v8_lvt l=880e-9   w=10e-6    nf=2
    M8  vcas  vcas  VDD   VDD sky130_fd_pr__pfet_01v8_lvt l=360e-9   w=2.5e-6   nf=1
    M5  OUT   out1  VDD   VDD sky130_fd_pr__pfet_01v8_lvt l=440e-9   w=16.5e-6  nf=1
    M3  out1  net18 VDD   VDD sky130_fd_pr__pfet_01v8_lvt l=2e-6     w=5e-6     nf=2
    M4  net18 net18 VDD   VDD sky130_fd_pr__pfet_01v8_lvt l=2e-6     w=5e-6     nf=2
    C0  net7  OUT             sky130_fd_pr__cap_mim_m3_1  l=40e-6    w=40e-6
.ends ota_ahuja