# olympus
design methOds for simpLifYing the creation of doMain-sPecific memory architectUreS

Necessary dependencies:

`python3`

Python dependencies:

`pip3 install cgen`

Tested with Xilinx tools version 2021.1, change path to tools in `targetplatform/alveo/platform_cfg.Makefile`

## From inside a test folder: 

Generate files (Xilinx tools not necessary):

`make olympus`

Compile hardware (xclbin):

`make chw`

Generate only HLS sources:

`make hls`

Compile host executable:

`make chost`

Run system:

`make run`

Do it all in one shot:

`make chost chw run`

Change target by passing `TARGET={sw_emu|hw_emu|hw}` to make command. Default is `sw_emu`


## Dev:

Currently, the script doing the work is `src/code_generator/olympus_codegen.py` 
