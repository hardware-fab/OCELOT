########################################################
###### Magic netlist extraction
########################################################

export MAGIC=magic
export PDK_ROOT=${PDK_ROOT:-/usr/local/share/pdk}
export PDKPATH="$PDK_ROOT/sky130A"
export MAGTYPE=mag

MAGIC_RC="$PDKPATH/libs.tech/magic/sky130A.magicrc"
if [[ ! -r "$MAGIC_RC" ]]; then
    echo "Missing Magic startup file: $MAGIC_RC. Set PDK_ROOT to the directory containing sky130A." >&2
    exit 1
fi

MAGTYPE=$MAGTYPE $MAGIC -dnull -noconsole -rcfile "$MAGIC_RC" << EOF

crashbackups stop

drc on
drc check

gds readonly true
gds flatten true
gds rescale true

tech unlock *
cif istyle sky130(vendor)
gds read $1
load ${1%.gds} -dereference
select top cell

extract do local
extract do resistance
extract all

extresist all

ext2sim labels on
ext2sim

ext2spice extresist off
ext2spice cthresh 0
ext2spice format ngspice

ext2spice -o ./gds-extracted.spice

ext2spice extresist off
ext2spice lvs
ext2spice -o ./gds-extracted_lvs.spice

EOF
#\rm -rf *.ext
#mv *.ext ./results
#mv *gds-extracted* results
