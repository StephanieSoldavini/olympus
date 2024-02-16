SHELL         := /bin/bash
PLATFORM      := xilinx_u280_xdma_201920_3
##PLATFORM      := xilinx_u55c_gen3x16_xdma_base_3
#PLATFORM      := xilinx_u55c_gen3x16_xdma_3_202210_1

# Polimi alveo u280 2021.1
VITIS         := /opt/xilinx/Vitis/2021.1/settings64.sh
XILINX_XRT    := /opt/xilinx/xrt
XILINX_VIVADO := /tools/Xilinx/Vivado/2021.1

# Polimi alveo u55c / 2022.1
#VITIS         := /opt/archive/xilinx/Vitis/2022.1/settings64.sh
#XILINX_XRT    := /opt/xilinx/xrt_202210/opt/xilinx/xrt
#XILINX_VIVADO := /opt/archive/xilinx/Vivado/2022.1

#VITIS         := /tools/Xilinx/Vitis/2021.1/settings64.sh
#XILINX_VIVADO := /opt/xilinx/Vivado/2021.1

MAX_JOBS      ?= 8
