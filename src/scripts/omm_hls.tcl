if { $argc < 1 } {
    puts "usage: vitis_hls $argv0 \[filename\]"  
    exit
} 

open_project omm
set_top omm
add_files [lindex $argv 0]
open_solution "solution1" -flow_target vivado
set_part {xcu280-fsvh2892-2L-e}
create_clock -period 4.444 -name default
config_export -format ip_catalog -rtl verilog
#csim_design
csynth_design
#cosim_design
export_design -rtl verilog -format ip_catalog
