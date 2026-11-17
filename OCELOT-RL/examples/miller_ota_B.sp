.subckt miller_ota INM INP GND VDD OUT VBIAS
    M0   net10 INM   net11 GND  sky130_fd_pr__nfet_01v8 l=1.5e-07  w=5e-06  nf=1
    M2   out1  INP   net11 GND  sky130_fd_pr__nfet_01v8 l=1.5e-07  w=5e-06  nf=1
    M1   net11 VBIAS GND   GND  sky130_fd_pr__nfet_01v8 l=1.5e-07  w=3e-06  nf=1
    M10  VBIAS VBIAS GND   GND  sky130_fd_pr__nfet_01v8 l=1.5e-07 w=3e-06 nf=1
    M4   net10 net10 VDD   VDD  sky130_fd_pr__pfet_01v8 l=1.5e-07  w=1.5e-05  nf=1
    M3   out1  net10 VDD   VDD  sky130_fd_pr__pfet_01v8 l=1.5e-07  w=1.5e-05  nf=1
    M5   OUT   out1  VDD   VDD  sky130_fd_pr__pfet_01v8 l=1.5e-07  w=6e-05  nf=1
    M6   OUT   VBIAS GND   GND  sky130_fd_pr__nfet_01v8 l=1.5e-07  w=1.5e-05  nf=1
    XR0   out1  net12 GND         sky130_fd_pr__res_xhigh_po_5p73 r=2500
    C0   net12 OUT               sky130_fd_pr__cap_mim_m3_1 l=20e-6 w=20e-6
.ends miller_ota
