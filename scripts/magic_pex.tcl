# Stage 8 PEX extract: GDS -> coupled R/C extraction -> SPICE (EDA only).
# `extract all` plus zero thresholds force every parasitic into the
# netlist (default thresholds silently drop femtofarad caps on demo-size
# cells). Run from the target directory (cwd contract, like the LVS
# script): magic -dnull -noconsole -T <sky130A.tech> < scripts/magic_pex.tcl
gds read pcell.gds
load pcell_nmos
extract all
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
quit -noprompt
