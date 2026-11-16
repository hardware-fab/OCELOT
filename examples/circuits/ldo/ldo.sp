.subckt ldo VIN VREF VDD GND VOUT

    M0 source VREF GND    GND sky130_fd_pr__nfet_01v8 l=5.000e-07  w=3.100e-06 nf=1
    M1 verr   VREF source GND sky130_fd_pr__nfet_01v8 l=5.000e-07  w=3.100e-06 nf=1
    M2 net8   vfb  source GND sky130_fd_pr__nfet_01v8 l=225.000e-9 w=3.600e-06 nf=1
    M3 verr   net8 VDD    VDD sky130_fd_pr__pfet_01v8 l=5.000e-07  w=3.500e-06 nf=1
    M4 net8   net8 VDD    VDD sky130_fd_pr__pfet_01v8 l=5.000e-07  w=3.500e-06 nf=1

    MP   VOUT  verr VIN VDD sky130_fd_pr__pfet_01v8    l=5.000e-07  w=3.500e-06 nf=1
    CL   VOUT  GND          sky130_fd_pr__cap_mim_m3_1 l=30e-6      w=30e-6
    XRF1 VOUT  vfb  GND     sky130_fd_pr__res_xhigh_po r=15k
    XRF2 vfb   GND  GND     sky130_fd_pr__res_xhigh_po r=10k

.ends ldo