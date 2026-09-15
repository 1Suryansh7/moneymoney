# Stage 8 spike M: Magic batch smoke (EDA only).
# Loads sky130A tech, paints one metal1 box, saves, runs DRC.
# Run from the target directory (save is cwd-relative by contract):
#   magic -dnull -noconsole -T <sky130A.tech> < scripts/magic_spike.tcl
box 0 0 200 100
paint metal1
save spike_magic
drc check
drc why
quit -noprompt
