#!/bin/bash
set -euo pipefail

SP_DIR=${1:-}

if [[ -z $SP_DIR ]]; then
    echo "Missing argument SP_DIR"
    exit 1
fi

SP_DIR=$(cd -- "$SP_DIR" && pwd)
SP_NL=$(basename -- "$SP_DIR")
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
run_python() {
    local helper=$1
    shift
    if [[ -n ${OCELOT_LVS_PYTHON:-} ]]; then
        "$OCELOT_LVS_PYTHON" --lvs-helper "$helper" "$@"
    else
        python3 "$SCRIPT_DIR/$helper" "$@"
    fi
}
GDS_TOP=$(run_python cell_name.py "$SP_NL")
SP_FILE="$SP_DIR/${SP_NL}.sp"
FLAT_NETLIST="$SP_DIR/${SP_NL}_flat.lvs.spice"
GDS_FILE="${SP_NL}_flat.gds"
EXTRACTED_NETLIST="$SP_DIR/gds-extracted_lvs.spice"

echo "I received SP_DIR: $SP_DIR SP_NL: $SP_NL GDS_TOP: $GDS_TOP"

if [[ ! -f "$SP_FILE" ]]; then
    echo "Missing SPICE netlist: $SP_FILE" >&2
    exit 1
fi

run_python 0_sp2lvs.py "$SP_FILE" "$FLAT_NETLIST" --top-name "${SP_NL}_flat"

if [[ ! -f "$SP_DIR/$GDS_FILE" ]]; then
    echo "Missing GDS for LVS extraction: $SP_DIR/$GDS_FILE" >&2
    exit 1
fi

(
    cd "$SP_DIR"
    bash "$SCRIPT_DIR/1_pex.sh" "$GDS_FILE" "${GDS_TOP}_flat"
)

if [[ ! -f "$EXTRACTED_NETLIST" ]]; then
    echo "Magic extraction did not create: $EXTRACTED_NETLIST" >&2
    exit 1
fi

run_python 3_patch_extracted_top_ports.py "$EXTRACTED_NETLIST" "$FLAT_NETLIST" "${SP_NL}_flat"

(
    cd "$SP_DIR"
    netgen -batch lvs "gds-extracted_lvs.spice ${GDS_TOP}_flat" "${SP_NL}_flat.lvs.spice ${SP_NL}_flat" "$SCRIPT_DIR/2_netgen_setup.tcl"
    rm -f ./*.ext
)
