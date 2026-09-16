# Stage 8 LVS extract: GDS -> Magic extraction -> SPICE (EDA only).
# Run from the target directory (all files cwd-relative by contract):
#   magic -dnull -noconsole -T <sky130A.tech> < scripts/magic_extract.tcl
gds read pcell.gds
load pcell_nmos
extract
ext2spice
quit -noprompt
