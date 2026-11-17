from pathlib import Path
import numpy as np
import time
from .config import MATCHING_GROUPS, CORNER_VDD_MAP, VDD_VOLTS, PDK_LIB_PATH, TOPOLOGY, NGSPICE_SEM, RESULTS_ROOT, LAYOUT_EXECUTABLE, DRC_FILE, LAYOUT_SUBCKT_NAME, json, os, subprocess
OCELOT_MAX_RETRIES = 3
OCELOT_RETRY_DELAY = 1

def sizing_to_full(sizing):
    full = {}
    for group, members in MATCHING_GROUPS.items():
        for m in members:
            full[f'{m}.l'] = float(sizing[f'{group}.l'])
            full[f'{m}.w'] = float(sizing[f'{group}.w'])
            full[f'{m}.nf'] = int(sizing[f'{group}.nf'])
    return full

def _build_subckt_spice_five_transistors(sizing):
    full = sizing_to_full(sizing)
    lines = ['* Pre-layout subcircuit — five_transistors_ota', '.subckt five_transistors_ota GND VDD VOUT VINN VINP VBIAS', f"    X0 source VBIAS GND GND sky130_fd_pr__nfet_01v8 l={full['X0.l'] * 1e-06:g} w={full['X0.w'] * 1e-06:g} nf={full['X0.nf']}", f"    X1 net8 VINP source GND sky130_fd_pr__nfet_01v8 l={full['X1.l'] * 1e-06:g} w={full['X1.w'] * 1e-06:g} nf={full['X1.nf']}", f"    X2 VOUT VINN source GND sky130_fd_pr__nfet_01v8 l={full['X2.l'] * 1e-06:g} w={full['X2.w'] * 1e-06:g} nf={full['X2.nf']}", f"    X3 net8 net8 VDD VDD sky130_fd_pr__pfet_01v8 l={full['X3.l'] * 1e-06:g} w={full['X3.w'] * 1e-06:g} nf={full['X3.nf']}", f"    X4 VOUT net8 VDD VDD sky130_fd_pr__pfet_01v8 l={full['X4.l'] * 1e-06:g} w={full['X4.w'] * 1e-06:g} nf={full['X4.nf']}", '    X5 VOUT GND sky130_fd_pr__cap_mim_m3_1 l=20e-6 w=20e-6', '.ends five_transistors_ota']
    return '\n'.join(lines)

def _build_subckt_spice_ahuja(sizing):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = ['* Pre-layout subcircuit — ota_ahuja', '.subckt ota_ahuja INM INP GND VDD VBIAS OUT', f"    XM7  VDD   out1  net1  GND  {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    XM11 net11 VBIAS GND   GND  {_nfet} l={_f('XM11.l')} w={_f('XM11.w')} nf={full['XM11.nf']}", f"    XM12 VBIAS VBIAS GND   GND  {_nfet} l={_f('XM12.l')} w={_f('XM12.w')} nf={full['XM12.nf']}", f"    XM9  net1  VBIAS GND   GND  {_nfet} l={_f('XM9.l')} w={_f('XM9.w')} nf={full['XM9.nf']}", f"    XM6  OUT   net1  GND   GND  {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f"    XM5  OUT   out1  VDD   VDD  {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    XMC1 out1  vcas  net7  GND  {_nfet} l={_f('XMC1.l')} w={_f('XMC1.w')} nf={full['XMC1.nf']}", f"    XMC2 net18 vcas  net16 GND  {_nfet} l={_f('XMC2.l')} w={_f('XMC2.w')} nf={full['XMC2.nf']}", f"    XM2  net16 INM   net11 GND  {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    XM1  net7  INP   net11 GND  {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f'    XC0  net7  OUT   {_cap} l=8 w=8', f"    XM8  vcas  vcas  VDD   VDD  {_pfet} l={_f('XM8.l')} w={_f('XM8.w')} nf={full['XM8.nf']}", f"    XM3  out1  net18 VDD   VDD  {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    XM4  net18 net18 VDD   VDD  {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", '.ends ota_ahuja']
    return '\n'.join(lines)

def _build_subckt_spice_hpf(sizing):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = ['* Pre-layout subcircuit — hpf', '.subckt hpf GND VDD VOUT VINN VINP VBIAS VFILTER', f"    XM0 tail  VBIAS GND  GND  {_nfet} l={_f('XM0.l')} w={_f('XM0.w')} nf={full['XM0.nf']}", f"    XM7 VBIAS VBIAS GND  GND  {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    XM1 net1  VINN  tail GND  {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f"    XM2 net2  VINP  tail GND  {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    XM3 net1  net1  VDD  VDD  {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    XM4 net2  net1  VDD  VDD  {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", f"    XM5 VOUT  net2  VDD  VDD  {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    XM6 VOUT  net2  GND  GND  {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f'    XR0  net2      net2_comp GND  {_hpo} r=1500', f'    XC0  net2_comp VOUT           {_cap} l=4e-6  w=4e-6', f'    XC1  VOUT      GND            {_cap} l=5e-6  w=5e-6', f'    XC2  VOUT      VFILTER        {_cap} l=30e-6 w=30e-6', f'    XR1  VFILTER   GND  GND       {_hpo} r=1500', '.ends hpf']
    return '\n'.join(lines)

def _build_subckt_spice_lpf(sizing):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = ['* Pre-layout subcircuit — lpf', '.subckt lpf GND VDD VOUT VINN VINP VBIAS VFILTER', f"    XM0 tail  VBIAS GND  GND  {_nfet} l={_f('XM0.l')} w={_f('XM0.w')} nf={full['XM0.nf']}", f"    XM7 VBIAS VBIAS GND  GND  {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    XM1 net1  VINN  tail GND  {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f"    XM2 net2  VINP  tail GND  {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    XM3 net1  net1  VDD  VDD  {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    XM4 net2  net1  VDD  VDD  {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", f"    XM5 VOUT  net2  VDD  VDD  {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    XM6 VOUT  net2  GND  GND  {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f'    XR0 net2      net2_int GND  {_hpo} r=20000', f'    XC0 net2_int  VOUT          {_cap} l=21e-6 w=21e-6', f'    XC1 VOUT      GND           {_cap} l=5e-6  w=5e-6', f'    XR1 VOUT      VFILTER GND   {_hpo} r=5000', f'    XC2 VFILTER   GND           {_cap} l=80e-6 w=80e-6', '.ends lpf']
    return '\n'.join(lines)

def _build_subckt_spice_miller(sizing):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = ['* Pre-layout subcircuit — miller_ota', '.subckt miller_ota INM INP GND VDD OUT VBIAS', f"    XM0  net10 INM   net11 GND  {_nfet} l={_f('M0.l')}  w={_f('M0.w')}  nf={full['M0.nf']}", f"    XM2  out1  INP   net11 GND  {_nfet} l={_f('M2.l')}  w={_f('M2.w')}  nf={full['M2.nf']}", f"    XM1  net11 VBIAS GND   GND  {_nfet} l={_f('M1.l')}  w={_f('M1.w')}  nf={full['M1.nf']}", f"    XM10 VBIAS VBIAS GND   GND  {_nfet} l={_f('M10.l')} w={_f('M10.w')} nf={full['M10.nf']}", f"    XM4  net10 net10 VDD   VDD  {_pfet} l={_f('M4.l')}  w={_f('M4.w')}  nf={full['M4.nf']}", f"    XM3  out1  net10 VDD   VDD  {_pfet} l={_f('M3.l')}  w={_f('M3.w')}  nf={full['M3.nf']}", f"    XM5  OUT   out1  VDD   VDD  {_pfet} l={_f('M5.l')}  w={_f('M5.w')}  nf={full['M5.nf']}", f"    XM6  OUT   VBIAS GND   GND  {_nfet} l={_f('M6.l')}  w={_f('M6.w')}  nf={full['M6.nf']}", f'    XR0  out1  net12 GND         {_hpo} r=2500', f'    XC0  net12 OUT               {_cap} l=20e-6 w=20e-6', '.ends miller_ota']
    return '\n'.join(lines)

def build_subckt_spice(sizing):
    if TOPOLOGY == 'five_transistors':
        return _build_subckt_spice_five_transistors(sizing)
    elif TOPOLOGY == 'ahuja_ota':
        return _build_subckt_spice_ahuja(sizing)
    elif TOPOLOGY == 'hpf':
        return _build_subckt_spice_hpf(sizing)
    elif TOPOLOGY == 'lpf':
        return _build_subckt_spice_lpf(sizing)
    elif TOPOLOGY == 'miller_ota':
        return _build_subckt_spice_miller(sizing)
    else:
        raise ValueError(f'build_subckt_spice: unsupported TOPOLOGY={TOPOLOGY!r}')

def write_step_netlist(sizing, step_dir):
    suffix = 'sp'
    (Path(step_dir) / f'netlist.{suffix}').write_text(build_subckt_spice(sizing))

def build_five_transistors_testbench(sizing, corner, temp, metrics_path):
    full = sizing_to_full(sizing)
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vcm = round(vdd_val * 0.5, 3)
    vbias = round(vdd_val * 0.333, 3)
    mp = metrics_path.as_posix()
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', '.subckt five_transistors_ota GND VDD VOUT VINN VINP VBIAS', f"    X0 source VBIAS GND GND sky130_fd_pr__nfet_01v8 l={full['X0.l'] * 1e-06:g} w={full['X0.w'] * 1e-06:g} nf={full['X0.nf']}", f"    X1 net8 VINP source GND sky130_fd_pr__nfet_01v8 l={full['X1.l'] * 1e-06:g} w={full['X1.w'] * 1e-06:g} nf={full['X1.nf']}", f"    X2 VOUT VINN source GND sky130_fd_pr__nfet_01v8 l={full['X2.l'] * 1e-06:g} w={full['X2.w'] * 1e-06:g} nf={full['X2.nf']}", f"    X3 net8 net8 VDD VDD sky130_fd_pr__pfet_01v8 l={full['X3.l'] * 1e-06:g} w={full['X3.w'] * 1e-06:g} nf={full['X3.nf']}", f"    X4 VOUT net8 VDD VDD sky130_fd_pr__pfet_01v8 l={full['X4.l'] * 1e-06:g} w={full['X4.w'] * 1e-06:g} nf={full['X4.nf']}", '    X5 VOUT GND sky130_fd_pr__cap_mim_m3_1 l=20e-6 w=20e-6', '.ends five_transistors_ota', '', *_ota_testbench_body('five_transistors_ota', vcm, vdd_val, vbias, mp)]
    return '\n'.join(lines)

def _ota_testbench_body(subckt_name, vcm, vdd_val, vbias, mp, instance_line=None):
    if instance_line is None:
        instance_line = f'xota_ol GND VDD VOUT_OL vinn_ol vin_ol vbias_ol {subckt_name}'
    return ['* ── Open-loop instance ───────────────────────────────────────────────────────────', instance_line, f'Vin_ol    vin_ol    GND  dc {vcm} ac 1', f'Vinn_ol   vinn_ol   GND  dc {vcm} ac 0', f'Vcc       VDD       GND  dc {vdd_val} ac 0', f'Vbias     vbias_ol  GND  dc {vbias}', '', '.ac dec 100 1 1G', '', '.control', '', '    * ====== 1. Open-loop gain + PM ======', '    alter @Vin_ol[acmag]  = 1', '    alter @Vinn_ol[acmag] = 0', '    alter @Vcc[acmag]     = 0', '    run', '    let phase_deg = ph(v(VOUT_OL)) * 180 / 3.14159265', '    meas ac dc_gain MAX vdb(VOUT_OL)', '    set dc_gain_num = "$&dc_gain"', '    * ugbw / pm: pre-init sentinels so a no-UGF circuit writes -2e99, not blank', '    set ugbw_num = "-2e99"', '    set pm_num   = "-2e99"', '    let ugbw        = -2e99', '    let phase_at_ug = -2e99', '    meas ac ugbw        WHEN vdb(VOUT_OL) = 0', '    meas ac phase_at_ug FIND phase_deg WHEN vdb(VOUT_OL) = 0', '    if ( ugbw > 0 )', '        set ugbw_num = "$&ugbw"', '        let pm_val   = 180 + phase_at_ug', '        set pm_num   = "$&pm_val"', '    end', '', '    * ====== 2. CMRR ======', '    alter @Vin_ol[acmag]  = 1', '    alter @Vinn_ol[acmag] = 1', '    alter @Vcc[acmag]     = 0', '    run', '    meas ac cm_gain_dc MAX vdb(VOUT_OL)', '    let cmrr = $dc_gain_num - cm_gain_dc', '    set cmrr_num = "$&cmrr"', '', '    * ====== 3. PSRR ======', '    alter @Vin_ol[acmag]  = 0', '    alter @Vinn_ol[acmag] = 0', '    alter @Vcc[acmag]     = 0.15', '    run', '    meas ac supply_gain_dc MAX vdb(VOUT_OL)', '    let psrr_val = $dc_gain_num - supply_gain_dc', '    set psrr_num = "$&psrr_val"', '', '    * ====== 4. Write scalar metrics ======', f'    echo "dc_gain_dB = $dc_gain_num"  > {mp}', f'    echo "ugbw_Hz = $ugbw_num"        >> {mp}', f'    echo "pm_deg = $pm_num"           >> {mp}', f'    echo "cmrr_dB = $cmrr_num"        >> {mp}', f'    echo "psrr_dB = $psrr_num"        >> {mp}', '', '    quit', '.endc', '', '.end']

def parse_metrics_txt(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if '=' not in line:
            continue
        key, _, val_str = line.partition('=')
        try:
            v = float(val_str.strip())
            result[key.strip()] = None if abs(v) > 1e+99 else v
        except ValueError:
            result[key.strip()] = None
    return result
NGSPICE_TIMEOUT = 300

def run_ngspice_deck(spice_path):
    with NGSPICE_SEM:
        cmd = ['ngspice', '-b', str(spice_path)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=NGSPICE_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise RuntimeError(f'ngspice timed out after {NGSPICE_TIMEOUT}s for {spice_path}')
    if proc.returncode != 0:
        raise RuntimeError(f'ngspice failed for {spice_path}\nSTDOUT:\n{stdout[-3000:]}\nSTDERR:\n{stderr[-1000:]}')

def get_step_dir(ep_idx, st_idx):
    p = get_episode_dir(ep_idx) / f'step_{st_idx:04d}'
    p.mkdir(parents=True, exist_ok=True)
    return p

def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2))
SCALAR_METRICS = ['dc_gain_dB', 'ugbw_Hz', 'f3db_Hz', 'gbw_Hz', 'pm_deg', 'supply_gain_dc_dB', 'psrr_dB', 'cm_gain_dc_dB', 'cmrr_dB', 'passband_gain_dB', 'cutoff_freq_Hz', 'stopband_attenuation_dB']

class OCELOTFailure(RuntimeError):
    pass

def _write_sp_for_ocelot_five_transistors(sizing, sp_path):
    full = sizing_to_full(sizing)
    lines = [f'.subckt {LAYOUT_SUBCKT_NAME} GND VDD VOUT VINN VINP VBIAS', f"    M0 source VBIAS GND GND sky130_fd_pr__nfet_01v8 l={full['X0.l'] * 1e-06:g} w={full['X0.w'] * 1e-06:g} nf={full['X0.nf']}", f"    M1 net8 VINP source GND sky130_fd_pr__nfet_01v8 l={full['X1.l'] * 1e-06:g} w={full['X1.w'] * 1e-06:g} nf={full['X1.nf']}", f"    M2 VOUT VINN source GND sky130_fd_pr__nfet_01v8 l={full['X2.l'] * 1e-06:g} w={full['X2.w'] * 1e-06:g} nf={full['X2.nf']}", f"    M3 net8 net8 VDD    VDD sky130_fd_pr__pfet_01v8 l={full['X3.l'] * 1e-06:g} w={full['X3.w'] * 1e-06:g} nf={full['X3.nf']}", f"    M4 VOUT net8 VDD    VDD sky130_fd_pr__pfet_01v8 l={full['X4.l'] * 1e-06:g} w={full['X4.w'] * 1e-06:g} nf={full['X4.nf']}", f'    C5 VOUT GND sky130_fd_pr__cap_mim_m3_1 l=20e-6 w=20e-6', f'.ends {LAYOUT_SUBCKT_NAME}']
    Path(sp_path).write_text('\n'.join(lines) + '\n')

def _write_sp_for_ocelot_ahuja(sizing, sp_path):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = [f'.subckt {LAYOUT_SUBCKT_NAME} INM INP GND VDD VBIAS OUT', f"    M1  net7  INP   net11 GND {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f"    M2  net16 INM   net11 GND {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    MC1 out1  vcas  net7  GND {_nfet} l={_f('XMC1.l')} w={_f('XMC1.w')} nf={full['XMC1.nf']}", f"    MC2 net18 vcas  net16 GND {_nfet} l={_f('XMC2.l')} w={_f('XMC2.w')} nf={full['XMC2.nf']}", f"    M3  out1  net18 VDD   VDD {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    M4  net18 net18 VDD   VDD {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", f"    M11 net11 VBIAS GND   GND {_nfet} l={_f('XM11.l')} w={_f('XM11.w')} nf={full['XM11.nf']}", f"    M12 VBIAS VBIAS GND   GND {_nfet} l={_f('XM12.l')} w={_f('XM12.w')} nf={full['XM12.nf']}", f"    M5  OUT   out1  VDD   VDD {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    M6  OUT   net1  GND   GND {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f"    M7  VDD   out1  net1  GND {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    M8  vcas  vcas  VDD   VDD {_pfet} l={_f('XM8.l')} w={_f('XM8.w')} nf={full['XM8.nf']}", f"    M9  net1  VBIAS GND   GND {_nfet} l={_f('XM9.l')} w={_f('XM9.w')} nf={full['XM9.nf']}", f'    C0  net7  OUT   {_cap} l=5e-6 w=5e-6', f'.ends {LAYOUT_SUBCKT_NAME}']
    Path(sp_path).write_text('\n'.join(lines) + '\n')

def _write_sp_for_ocelot_hpf(sizing, sp_path):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = [f'.subckt {LAYOUT_SUBCKT_NAME} GND VDD VOUT VINN VINP VBIAS VFILTER', f"    M0  tail  VBIAS GND  GND  {_nfet} l={_f('XM0.l')} w={_f('XM0.w')} nf={full['XM0.nf']}", f"    M7  VBIAS VBIAS GND  GND  {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    M1  net1  VINN  tail GND  {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f"    M2  net2  VINP  tail GND  {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    M3  net1  net1  VDD  VDD  {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    M4  net2  net1  VDD  VDD  {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", f"    M5  VOUT  net2  VDD  VDD  {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    M6  VOUT  net2  GND  GND  {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f'    XRz  net2      net2_comp GND  {_hpo} l=2e-6  w=5.73e-6', f'    Cc  net2_comp VOUT           {_cap} l=4e-6  w=4e-6', f'    CL  VOUT      GND            {_cap} l=5e-6  w=5e-6', f'    C1  VOUT      VFILTER        {_cap} l=90e-6 w=90e-6', f'    XR1  VFILTER   GND  GND       {_hpo} l=50e-6 w=5.73e-6', f'.ends {LAYOUT_SUBCKT_NAME}']
    Path(sp_path).write_text('\n'.join(lines) + '\n')

def _write_sp_for_ocelot_lpf(sizing, sp_path):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = [f'.subckt {LAYOUT_SUBCKT_NAME} GND VDD VOUT VINN VINP VBIAS VFILTER', f"    M0  tail  VBIAS GND  GND  {_nfet} l={_f('XM0.l')} w={_f('XM0.w')} nf={full['XM0.nf']}", f"    M7  VBIAS VBIAS GND  GND  {_nfet} l={_f('XM7.l')} w={_f('XM7.w')} nf={full['XM7.nf']}", f"    M1  net1  VINN  tail GND  {_nfet} l={_f('XM1.l')} w={_f('XM1.w')} nf={full['XM1.nf']}", f"    M2  net2  VINP  tail GND  {_nfet} l={_f('XM2.l')} w={_f('XM2.w')} nf={full['XM2.nf']}", f"    M3  net1  net1  VDD  VDD  {_pfet} l={_f('XM3.l')} w={_f('XM3.w')} nf={full['XM3.nf']}", f"    M4  net2  net1  VDD  VDD  {_pfet} l={_f('XM4.l')} w={_f('XM4.w')} nf={full['XM4.nf']}", f"    M5  VOUT  net2  VDD  VDD  {_pfet} l={_f('XM5.l')} w={_f('XM5.w')} nf={full['XM5.nf']}", f"    M6  VOUT  net2  GND  GND  {_nfet} l={_f('XM6.l')} w={_f('XM6.w')} nf={full['XM6.nf']}", f'    XRz  net2      net2_int GND  {_hpo} l=57.27e-6 w=5.73e-6', f'    Cc  net2_int  VOUT           {_cap} l=21e-6    w=21e-6', f'    CL  VOUT      GND            {_cap} l=5e-6     w=5e-6', f'    XR1  VOUT      VFILTER GND    {_hpo} l=14.3e-6  w=5.73e-6', f'    C2  VFILTER   GND            {_cap} l=80e-6    w=80e-6', f'.ends {LAYOUT_SUBCKT_NAME}']
    Path(sp_path).write_text('\n'.join(lines) + '\n')

def _write_sp_for_ocelot_miller(sizing, sp_path):
    full = sizing_to_full(sizing)
    _nfet = 'sky130_fd_pr__nfet_01v8'
    _pfet = 'sky130_fd_pr__pfet_01v8'
    _cap = 'sky130_fd_pr__cap_mim_m3_1'
    _hpo = 'sky130_fd_pr__res_xhigh_po_5p73'

    def _f(name):
        return f'{full[name] * 1e-06:g}'
    lines = [f'.subckt {LAYOUT_SUBCKT_NAME} INM INP GND VDD OUT VBIAS', f"    M0   net10 INM   net11 GND  {_nfet} l={_f('M0.l')}  w={_f('M0.w')}  nf={full['M0.nf']}", f"    M2   out1  INP   net11 GND  {_nfet} l={_f('M2.l')}  w={_f('M2.w')}  nf={full['M2.nf']}", f"    M1   net11 VBIAS GND   GND  {_nfet} l={_f('M1.l')}  w={_f('M1.w')}  nf={full['M1.nf']}", f"    M10  VBIAS VBIAS GND   GND  {_nfet} l={_f('M10.l')} w={_f('M10.w')} nf={full['M10.nf']}", f"    M4   net10 net10 VDD   VDD  {_pfet} l={_f('M4.l')}  w={_f('M4.w')}  nf={full['M4.nf']}", f"    M3   out1  net10 VDD   VDD  {_pfet} l={_f('M3.l')}  w={_f('M3.w')}  nf={full['M3.nf']}", f"    M5   OUT   out1  VDD   VDD  {_pfet} l={_f('M5.l')}  w={_f('M5.w')}  nf={full['M5.nf']}", f"    M6   OUT   VBIAS GND   GND  {_nfet} l={_f('M6.l')}  w={_f('M6.w')}  nf={full['M6.nf']}", f'    XR0   out1  net12 GND         {_hpo} r=2500', f'    C0   net12 OUT               {_cap} l=20e-6 w=20e-6', f'.ends {LAYOUT_SUBCKT_NAME}']
    Path(sp_path).write_text('\n'.join(lines) + '\n')

def write_sp_for_ocelot(sizing, sp_path):
    if TOPOLOGY == 'five_transistors':
        _write_sp_for_ocelot_five_transistors(sizing, sp_path)
    elif TOPOLOGY == 'ahuja_ota':
        _write_sp_for_ocelot_ahuja(sizing, sp_path)
    elif TOPOLOGY == 'hpf':
        _write_sp_for_ocelot_hpf(sizing, sp_path)
    elif TOPOLOGY == 'lpf':
        _write_sp_for_ocelot_lpf(sizing, sp_path)
    elif TOPOLOGY == 'miller_ota':
        _write_sp_for_ocelot_miller(sizing, sp_path)
    else:
        raise ValueError(f'write_sp_for_ocelot: unknown TOPOLOGY={TOPOLOGY!r}')

def parse_placement_state(placement_path):
    data = json.loads(Path(placement_path).read_text())
    blocks = data['subckt']['blocks']
    return {name: {'width': int(info['width']), 'height': int(info['height']), 'placed_x': int(info['placed_x']), 'placed_y': int(info['placed_y'])} for name, info in blocks.items()}

def build_five_transistors_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vcm = round(vdd_val * 0.5, 3)
    vbias = round(vdd_val * 0.333, 3)
    mp = metrics_path.as_posix()
    body_lines = [line for line in extracted_content.splitlines() if line.strip() and (not line.strip().startswith('*')) and (not line.strip().startswith('//'))]
    extracted_body = '\n'.join(body_lines)
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', f'* ── Post-layout extracted subckt (OCELOT / gds-extracted.spice) ──', f'.subckt {LAYOUT_SUBCKT_NAME} GND VDD VOUT VINN VINP VBIAS', extracted_body, f'.ends {LAYOUT_SUBCKT_NAME}', '', *_ota_testbench_body(LAYOUT_SUBCKT_NAME, vcm, vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_ahuja_testbench(sizing, corner, temp, metrics_path):
    full = sizing_to_full(sizing)
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.599
    mp = metrics_path.as_posix()
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', _build_subckt_spice_ahuja(sizing), '', *_ahuja_dual_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_ahuja_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.5
    mp = metrics_path.as_posix()
    body_lines = [line for line in extracted_content.splitlines() if line.strip() and (not line.strip().startswith('*')) and (not line.strip().startswith('//'))]
    extracted_body = '\n'.join(body_lines)
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', f'* ── Post-layout extracted subckt (OCELOT / gds-extracted.spice) ──', f'.subckt ota_ahuja INM INP GND VDD VBIAS OUT', extracted_body, f'.ends ota_ahuja', '', *_ahuja_dual_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def _ahuja_dual_testbench_body(vdd_val, vbias, mp):
    return ['* ── Instance 1: Open-Loop (For Gain, UGBW, PM) ───────────────────────────────────', 'xota_ol vinn_ol vin_ol GND VDD vbias_ol VOUT_OL ota_ahuja', f'Vpos_ol  vin_ol    GND  dc {vdd_val * 0.5:g}           $ DC bias for non-inverting', 'L_break  VOUT_OL   vinn_ol  1GH          $ DC short for biasing, AC open for gain', 'C_inject IN_AC     vinn_ol  1GF          $ Injection cap', f'Vin_AC   IN_AC     GND      dc {vdd_val * 0.5:g} ac 1  $ AC signal source for OLG', '', '* ── Instance 2: Closed-Loop Unity Gain (For CMRR, PSRR) ──────────────────────────', 'xota_cl VOUT_CL vin_cl GND VDD vbias_ol VOUT_CL ota_ahuja', f'Vcl_in   vin_cl    GND  dc {vdd_val * 0.5:g} ac 1      $ Input for common-mode injection', '', '* ── Global Supplies and Biasing ──────────────────────────────────────────────────', f'Vcc      VDD       GND      dc {vdd_val:g}   $ Main supply', f'Vbias    vbias_ol  GND      dc {vbias:g}     $ Tail current bias', '', '.ac dec 100 1 1G', '', '.control', '    * ====== 1. Open-loop gain + PM (Measured on Instance 1) ======', '    alter @Vin_AC[acmag] = 1', '    alter @Vcl_in[acmag] = 0', '    alter @Vcc[acmag]    = 0', '    run', '', '    let gain_vec = vdb(VOUT_OL) - vdb(vinn_ol)', '    let phase_deg = ph(v(VOUT_OL)/v(vinn_ol)) * 180 / 3.14159265', '    ', '    meas ac dc_gain MAX gain_vec', '    meas ac ugbw_val WHEN gain_vec = 0', '    meas ac phase_at_ug_val FIND phase_deg WHEN gain_vec = 0', '    ', '    set dc_val = "$&dc_gain"', '    set ugbw_num = "-2e99"', '    set pm_num   = "-2e99"', '', '    if ( $&ugbw_val > 0 )', '        set ugbw_num = "$&ugbw_val"', '        let pm_calc = 180 + $&phase_at_ug_val', '        set pm_num = "$&pm_calc"', '    end', '', '    * ====== 2. CMRR (Measured on Instance 2) ======', '    alter @Vin_AC[acmag] = 0', '    alter @Vcl_in[acmag] = 1', '    alter @Vcc[acmag]    = 0', '    run', '    ', '    meas ac cm_out_db MAX vdb(VOUT_CL)', '    let cmrr_val = ac1.dc_gain - $&cm_out_db', '    set cmrr_num = "$&cmrr_val"', '', '    * ====== 3. PSRR (Measured on Instance 2) ======', '    alter @Vin_AC[acmag] = 0', '    alter @Vcl_in[acmag] = 0', '    alter @Vcc[acmag]    = 1', '    run', '    ', '    meas ac psrr_out_db MAX vdb(VOUT_CL)', '    let psrr_final = ac1.dc_gain - $&psrr_out_db', '    set psrr_num = "$&psrr_final"', '', '    * ====== 4. Write scalar metrics ======', f'    echo "dc_gain_dB = $dc_val"     >  {mp}', f'    echo "ugbw_Hz = $ugbw_num"      >> {mp}', f'    echo "pm_deg = $pm_num"         >> {mp}', f'    echo "cmrr_dB = $cmrr_num"      >> {mp}', f'    echo "psrr_dB = $psrr_num"      >> {mp}', '    quit', '.endc']

def _miller_dual_testbench_body(vdd_val, vbias, mp):
    return ['* ── Instance 1: Open-Loop (For gain reference) ───────────────────────────────────', 'xota_ol vinn_ol vin_ol GND VDD VOUT_OL vbias_ol miller_ota', f'Vpos_ol  vin_ol    GND  dc {vdd_val * 0.5:g}           $ DC bias for non-inverting', 'L_break  VOUT_OL   vinn_ol  1GH          $ DC short for biasing, AC open for gain', 'C_inject IN_AC     vinn_ol  1GF          $ Injection cap', f'Vin_AC   IN_AC     GND      dc {vdd_val * 0.5:g} ac 1  $ AC signal source for OLG', '', '* ── Instance 2: Closed-Loop Unity Gain (For CMRR, PSRR) ──────────────────────────', 'xota_cl VOUT_CL vin_cl GND VDD VOUT_CL vbias_ol miller_ota', f'Vcl_in   vin_cl    GND  dc {vdd_val * 0.5:g} ac 1      $ Input for common-mode injection', '', '* ── Global Supplies and Biasing ──────────────────────────────────────────────────', f'Vcc      VDD       GND      dc {vdd_val:g}   $ Main supply', f'Vbias    vbias_ol  GND      dc {vbias:g}     $ Tail current bias', '', '.ac dec 100 1 1G', '', '.control', '    * ====== 1. Gain reference for CMRR/PSRR (Measured on Instance 1) ======', '    alter @Vin_AC[acmag] = 1', '    alter @Vcl_in[acmag] = 0', '    alter @Vcc[acmag]    = 0', '    run', '', '    let gain_vec = vdb(VOUT_OL) - vdb(vinn_ol)', '    ', '    meas ac dc_gain MAX gain_vec', '    ', '', '', '    * ====== 2. CMRR (Measured on Instance 2) ======', '    alter @Vin_AC[acmag] = 0', '    alter @Vcl_in[acmag] = 1', '    alter @Vcc[acmag]    = 0', '    run', '    ', '    meas ac cm_out_db MAX vdb(VOUT_CL)', '    let cmrr_val = ac1.dc_gain - $&cm_out_db', '    set cmrr_num = "$&cmrr_val"', '', '    * ====== 3. PSRR (Measured on Instance 2) ======', '    alter @Vin_AC[acmag] = 0', '    alter @Vcl_in[acmag] = 0', '    alter @Vcc[acmag]    = 1', '    run', '    ', '    meas ac psrr_out_db MAX vdb(VOUT_CL)', '    let psrr_final = ac1.dc_gain - $&psrr_out_db', '    set psrr_num = "$&psrr_final"', '', '    * ====== 4. Write scalar metrics ======', f'    echo "cmrr_dB = $cmrr_num"      > {mp}', f'    echo "psrr_dB = $psrr_num"      >> {mp}', '    quit', '.endc']

def build_miller_testbench(sizing, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.5
    mp = metrics_path.as_posix()
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', _build_subckt_spice_miller(sizing), '', *_miller_dual_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_miller_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.5
    mp = metrics_path.as_posix()
    body_lines = [line for line in extracted_content.splitlines() if line.strip() and (not line.strip().startswith('*')) and (not line.strip().startswith('//'))]
    extracted_body = '\n'.join(body_lines)
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', '* ── Post-layout extracted subckt (OCELOT / gds-extracted.spice) ──', '.subckt miller_ota INM INP GND VDD OUT VBIAS', extracted_body, '.ends miller_ota', '', *_miller_dual_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def _hpf_testbench_body(vdd_val, vbias, mp):
    vcm = round(vdd_val * 0.5, 3)
    return ['* ── HPF unity-feedback instance ───────────────────────────────────────────', 'Xhpf  GND VDD VOUT VOUT VINP VBIAS VFILTER  hpf', f'Vin   VINP  GND  dc {vcm} ac 1', f'Vbias VBIAS GND  dc {vbias}', f'Vdd   VDD   GND  dc {vdd_val}', '', '.ac dec 100 100 1G', '', '.control', '    run', '    * ====== Passband gain ======', '    meas ac passband_gain MAX vdb(VFILTER)', '    set passband_gain_num = "$&passband_gain"', '    * ====== Cutoff frequency (lower -3dB, HPF rising edge) ======', '    let thresh_3db = passband_gain - 3', '    let f_cutoff = -2e99', '    set f_cutoff_num = "-2e99"', '    meas ac f_cutoff WHEN vdb(VFILTER) = thresh_3db RISE=1', '    if ( f_cutoff > 0 )', '        set f_cutoff_num = "$&f_cutoff"', '    end', '    * ====== Stopband attenuation ======', '    meas ac gain_at_1k FIND vdb(VFILTER) AT=1000', '    let stopband_atten = passband_gain - gain_at_1k', '    set stopband_num = "$&stopband_atten"', f'    echo "passband_gain_dB = $passband_gain_num"    > {mp}', f'    echo "cutoff_freq_Hz = $f_cutoff_num"          >> {mp}', f'    echo "stopband_attenuation_dB = $stopband_num" >> {mp}', '    quit', '.endc', '', '.end']

def build_hpf_testbench(sizing, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.8
    mp = metrics_path.as_posix()
    subckt_lines = _build_subckt_spice_hpf(sizing).splitlines()
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', *subckt_lines, '', *_hpf_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_hpf_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.8
    mp = metrics_path.as_posix()
    body_lines = [line for line in extracted_content.splitlines() if line.strip() and (not line.strip().startswith('*')) and (not line.strip().startswith('//'))]
    extracted_body = '\n'.join(body_lines)
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', '* ── Post-layout extracted subckt (OCELOT / gds-extracted.spice) ──', '.subckt hpf GND VDD VOUT VINN VINP VBIAS VFILTER', extracted_body, '.ends hpf', '', *_hpf_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def _lpf_testbench_body(vdd_val, vbias, mp):
    vcm = round(vdd_val * 0.5, 3)
    return ['* ── LPF unity-feedback instance ───────────────────────────────────────────', 'Xlpf  GND VDD VOUT VOUT VINP VBIAS VFILTER  lpf', f'Vin   VINP  GND  dc {vcm} ac 1', f'Vbias VBIAS GND  dc {vbias}', f'Vdd   VDD   GND  dc {vdd_val}', '', '.ac dec 100 100 1G', '', '.control', '    run', '    * ====== Passband gain ======', '    meas ac passband_gain MAX vdb(VFILTER)', '    set passband_gain_num = "$&passband_gain"', '    * ====== Cutoff frequency (upper -3dB, LPF falling edge) ======', '    let thresh_3db = passband_gain - 3', '    let f_cutoff = -2e99', '    set f_cutoff_num = "-2e99"', '    meas ac f_cutoff WHEN vdb(VFILTER) = thresh_3db FALL=1', '    if ( f_cutoff > 0 )', '        set f_cutoff_num = "$&f_cutoff"', '    end', '    * ====== Stopband attenuation ======', '    meas ac gain_at_100M FIND vdb(VFILTER) AT=100000000', '    let stopband_atten = passband_gain - gain_at_100M', '    set stopband_num = "$&stopband_atten"', f'    echo "passband_gain_dB = $passband_gain_num"    > {mp}', f'    echo "cutoff_freq_Hz = $f_cutoff_num"          >> {mp}', f'    echo "stopband_attenuation_dB = $stopband_num" >> {mp}', '    quit', '.endc', '', '.end']

def build_lpf_testbench(sizing, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.8
    mp = metrics_path.as_posix()
    subckt_lines = _build_subckt_spice_lpf(sizing).splitlines()
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', *subckt_lines, '', *_lpf_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_lpf_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    vdd_key = CORNER_VDD_MAP[corner]
    vdd_val = VDD_VOLTS[vdd_key]
    vbias = 0.8
    mp = metrics_path.as_posix()
    body_lines = [line for line in extracted_content.splitlines() if line.strip() and (not line.strip().startswith('*')) and (not line.strip().startswith('//'))]
    extracted_body = '\n'.join(body_lines)
    lines = [f'.lib "{PDK_LIB_PATH}" {corner}', f'.temp {temp}', '', '* ── Post-layout extracted subckt (OCELOT / gds-extracted.spice) ──', '.subckt lpf GND VDD VOUT VINN VINP VBIAS VFILTER', extracted_body, '.ends lpf', '', *_lpf_testbench_body(vdd_val, vbias, mp)]
    return '\n'.join(lines)

def build_schematic_testbench(sizing, corner, temp, metrics_path):
    if TOPOLOGY == 'five_transistors':
        return build_five_transistors_testbench(sizing, corner, temp, metrics_path)
    elif TOPOLOGY == 'ahuja_ota':
        return build_ahuja_testbench(sizing, corner, temp, metrics_path)
    elif TOPOLOGY == 'hpf':
        return build_hpf_testbench(sizing, corner, temp, metrics_path)
    elif TOPOLOGY == 'lpf':
        return build_lpf_testbench(sizing, corner, temp, metrics_path)
    elif TOPOLOGY == 'miller_ota':
        return build_miller_testbench(sizing, corner, temp, metrics_path)
    raise ValueError(f'build_schematic_testbench: unknown TOPOLOGY={TOPOLOGY!r}')

def build_postlayout_testbench(extracted_content, corner, temp, metrics_path):
    if TOPOLOGY == 'five_transistors':
        return build_five_transistors_postlayout_testbench(extracted_content, corner, temp, metrics_path)
    elif TOPOLOGY == 'ahuja_ota':
        return build_ahuja_postlayout_testbench(extracted_content, corner, temp, metrics_path)
    elif TOPOLOGY == 'hpf':
        return build_hpf_postlayout_testbench(extracted_content, corner, temp, metrics_path)
    elif TOPOLOGY == 'lpf':
        return build_lpf_postlayout_testbench(extracted_content, corner, temp, metrics_path)
    elif TOPOLOGY == 'miller_ota':
        return build_miller_postlayout_testbench(extracted_content, corner, temp, metrics_path)
    raise ValueError(f'build_postlayout_testbench: unknown TOPOLOGY={TOPOLOGY!r}')

def get_episode_dir(ep_idx):
    p = RESULTS_ROOT / f'episode_{ep_idx:05d}'
    p.mkdir(parents=True, exist_ok=True)
    return p

def run_ocelot(folder_path):
    from .config import PDK_ROOT, LOCAL
    import signal
    env = dict(os.environ, PDK_ROOT=str(PDK_ROOT))
    cmd = [str(LAYOUT_EXECUTABLE), str(folder_path), str(DRC_FILE)]
    log = Path(folder_path).parent / 'layout.log'
    with log.open('w') as stream:
        proc = subprocess.Popen(cmd, cwd=LAYOUT_EXECUTABLE.parent, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=float(LOCAL.get('layout_timeout_seconds', 3600)))
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise OCELOTFailure(f'Layout timed out; see {log}')
    if code:
        raise OCELOTFailure(f'OCELOT exited with code {code}; see {log}')
