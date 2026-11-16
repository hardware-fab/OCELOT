.subckt five_transistors_ota VINN VINP VBIAS VDD GND VOUT
    M0 source VBIAS GND    GND sky130_fd_pr__nfet_01v8    l=0.5e-06 w=2.5e-06 nf=1
    M1 net8   VINP  source GND sky130_fd_pr__nfet_01v8    l=0.5e-06 w=2.5e-06 nf=1
    M2 VOUT   VINN  source GND sky130_fd_pr__nfet_01v8    l=0.5e-06 w=2.5e-06 nf=1
    M3 VOUT   net8  VDD    VDD sky130_fd_pr__pfet_01v8    l=0.5e-06 w=2.5e-06 nf=1
    M4 net8   net8  VDD    VDD sky130_fd_pr__pfet_01v8    l=0.5e-06 w=2.5e-06 nf=1
.ends five_transistors_ota

.subckt ota_composed VIN GND VDD VBIAS VOUT
    * Low Pass Filter
    X_OTA_5T_0 vlpf   ota_in VBIAS VDD GND vlpf five_transistors_ota
    XR0        VIN    ota_in GND                sky130_fd_pr__res_xhigh_po r=30k     
    C0         ota_in GND                       sky130_fd_pr__cap_mim_m3_1 l=20e-06 w=20e-06

    * High Pass filter
    X_OTA_5T_1 vr GND VBIAS VDD GND VOUT five_transistors_ota
    XR1        vr VOUT GND               sky130_fd_pr__res_xhigh_po r=30k     
    C1         vlpf vr                   sky130_fd_pr__cap_mim_m3_1 l=20e-06 w=20e-06
.ends
