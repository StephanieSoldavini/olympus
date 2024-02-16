#host code
HOST_SRC_NAMES = HostSampleTop.gen.cpp AlveoHost.cpp HostImpl.gen.cpp ../src/$(KERNEL_MODEL).cpp 
HOST_SRC   += $(addprefix $(SRC_OUT_DIR)/host/,$(HOST_SRC_NAMES)) 
EXEC_FLAGS ?=

#kernel code
CU_SRC     ?= CU.cpp 
ifeq ($(TARGET), sw_emu)
	kernel_as_hls_src = 1
endif
ifndef $(BLACKBOX)
	BLACKBOX ?= 0
endif
ifeq ($(BLACKBOX), 0)
	kernel_as_hls_src = 1
endif
ifdef kernel_as_hls_src
	CU_SRC += $(KERNEL_BODY).cpp
endif

KFLAGS     ?=
#run flags
#RUN_FLAGS  ?= $(N_CU) $(POINTS) /home/soldavini/olympus_soclab/olympus/tests/ptdr/ptdr_compute_profile1/HLS_output/simulation/values.txt
#RUN_FLAGS  ?= $(N_CU) $(POINTS) /home/soldavini/ptdr_64b_bambu/b/values.txt
RUN_FLAGS  ?= $(N_CU) $(POINTS) /home/soldavini/ptdr_repo/fcdhistoryanalytics/ptdr-cpp/data-generator/data1.bin

COMMONCFG     ?= $(BOARD_TARGET_PATH)/common.cfg

VERSION       ?= $(CU_NAME)
OPTS 	      ?= RB$(RING_BUF)_BW$(BUS_WIDTH)_S$(STREAMS)
CUR_DIR       ?= $(PWD)
TGT_DIR       ?= /opt/alveo_tests/olympus_tests
#TGT_DIR       ?= $(CUR_DIR)/out/
SRC_OUT_DIR   ?= $(TGT_DIR)/$(BENCH)/$(OPTS)-$(USER)/$(VERSION)/$(TEST)
RES_OUT_DIR   ?= $(SRC_OUT_DIR)/$(TARGET)

HLS_INCL	?=
HLS_FLAGS     ?= --hls.jobs $(MAX_JOBS) --save-temps $(HLS_INCL)
ifeq ($(BLACKBOX), 1)
	HLS_FLAGS += --hls.pre_tcl=$(SRC_OUT_DIR)/hlsPre.tcl
endif
#ifdef $(HLS_INCL)
#	HLS_FLAGS += -I$(HLS_INCL)
#endif

HLS_CFG       ?= $(CUR_DIR)/$(BOARD_TARGET_PATH)/runPre.tcl
IP_REPOS	?= --user_ip_repo_paths /home/soldavini/ptdr_bambu_ip --user_ip_repo_paths /home/soldavini/ptdr_hls_test
#VIVADO_FLAGS  ?= --vivado.impl.jobs $(MAX_JOBS) --vivado.synth.jobs $(MAX_JOBS) --save-temps --to_step vpl.config_hw_runs
#VIVADO_FLAGS2  ?= --vivado.impl.jobs $(MAX_JOBS) --vivado.synth.jobs $(MAX_JOBS) --save-temps --from_step vpl.synth
VIVADO_FLAGS  ?= --vivado.impl.jobs $(MAX_JOBS) --vivado.synth.jobs $(MAX_JOBS) $(IP_REPOS) --save-temps
HOST_FLAGS    ?= -I$(XILINX_XRT)/include/ -I$(XILINX_VIVADO)/include/  -Wall -O0 -g -std=c++11 $(HLS_INCL) $(USR_HOST_FLAGS)
HOST_LIBS     ?= -L$(XILINX_XRT)/lib/ -lOpenCL -lpthread -lrt -lstdc++ -I$(CUR_DIR)/$(BOARD_TARGET_PATH)/libs
EXEC_FLAGS    ?=

#ifdef $(HLS_INCL)
#	HOST_FLAGS += -I$(HLS_INCL)
#endif

DEBUG_FLAGS ?=#-g

#ADD_VHDL ?= --linkhook.do_first vpl.synth,$(CUR_DIR)/addVHDL.tcl
#ADD_VHDL ?= --linkhook.custom preSysLink,$(CUR_DIR)/addVHDL.tcl
#ADD_VHDL ?= --hls.post_tcl $(CUR_DIR)/addVHDL.tcl

LOG 		  ?= host_run_info_$(N_CU)cu_$$(date +%02Y%02m%02d%02H%02M%02S).txt

OLYMPUS	?= python3 ../../src/code_generator/olympus_codegen.py


all: run

$(RES_OUT_DIR)/results/$(CU_NAME).xo: $(addprefix $(SRC_OUT_DIR)/src/,$(CU_SRC)) $(SRC_OUT_DIR)/$(CFG)
	@echo "Setup environment"
	mkdir -p "$(RES_OUT_DIR)/build"
	mkdir -p "$(RES_OUT_DIR)/results"
	@echo "Perform HLS (compile hardware)"
	cd "$(RES_OUT_DIR)/build"; source $(VITIS); source $(XILINX_XRT)/setup.sh; v++ $(DEBUG_FLAGS) -c -t $(TARGET) $(KFLAGS) $(HLS_FLAGS) --config $(CUR_DIR)/$(COMMONCFG) --kernel_frequency $(FREQ) $(HLS_CFG) -k $(CU_NAME) -I$(SRC_OUT_DIR)/src  -o $(RES_OUT_DIR)/results/$(CU_NAME).xo $(addprefix $(SRC_OUT_DIR)/src/,$(CU_SRC))
	#cp $(CUR_DIR)/input/rtl/*.vhdl $(RES_OUT_DIR)/build/_x/krnl_helm/krnl_helm/krnl_helm/solution/syn/verilog/ 
	#ls -l $(RES_OUT_DIR)/results
	#cd "$(RES_OUT_DIR)/build/_x/krnl_helm/krnl_helm/"; source $(VITIS); source $(XILINX_XRT)/setup.sh; vitis_hls -f $(CUR_DIR)/addVHDL.tcl
	#ls -l $(RES_OUT_DIR)/results

$(RES_OUT_DIR)/results/$(CU_NAME)_$(N_CU)CU.xclbin: $(RES_OUT_DIR)/results/$(CU_NAME).xo $(SRC_OUT_DIR)/$(CFG)
	@echo "Setup environment" 
	mkdir -p "$(RES_OUT_DIR)/build"
	mkdir -p "$(RES_OUT_DIR)/results"
	@echo "Generate bitstream for $(N_CU) CUs (link hardware)"
	cd "$(RES_OUT_DIR)/build"; source $(VITIS); source $(XILINX_XRT)/setup.sh; v++ $(DEBUG_FLAGS) -l -t $(TARGET) $(VIVADO_FLAGS) --config $(CUR_DIR)/$(COMMONCFG) --kernel_frequency $(FREQ) --config $(SRC_OUT_DIR)/$(CFG) -o $(RES_OUT_DIR)/results/$(CU_NAME)_$(N_CU)CU.xclbin $(RES_OUT_DIR)/results/$(CU_NAME).xo

chw2:
	@echo "Setup environment" 
	mkdir -p "$(RES_OUT_DIR)/build"
	mkdir -p "$(RES_OUT_DIR)/results"
	@echo "Generate bitstream for $(N_CU) CUs (link hardware) ** TWO **"
	cd "$(RES_OUT_DIR)/build"; source $(VITIS); source $(XILINX_XRT)/setup.sh; v++ $(DEBUG_FLAGS) -l -t $(TARGET) $(VIVADO_FLAGS2) --config $(CUR_DIR)/$(COMMONCFG) --kernel_frequency $(FREQ) --config $(SRC_OUT_DIR)/$(CFG) -o $(RES_OUT_DIR)/results/$(CU_NAME)_$(N_CU)CU.xclbin $(RES_OUT_DIR)/results/$(CU_NAME).xo

$(RES_OUT_DIR)/results/RunHardware.exe: $(HOST_SRC)
	@echo "Setup environment"
	mkdir -p "$(RES_OUT_DIR)/build"
	mkdir -p "$(RES_OUT_DIR)/results"
	cp $(CUR_DIR)/$(BOARD_TARGET_PATH)/xrt.ini "$(RES_OUT_DIR)/results"
	@echo "Compile Host for $(N_CU) CUs"
	cd "$(RES_OUT_DIR)/build"; source $(VITIS); source $(XILINX_XRT)/setup.sh; g++ $(DEBUG_FLAGS) $(HOST_FLAGS) $(HOST_SRC) $(CUR_DIR)/$(BOARD_TARGET_PATH)/libs/xcl2.cpp  -o $(RES_OUT_DIR)/results/RunHardware.exe $(HOST_LIBS) $(EXEC_FLAGS)

#$(OLYMPUS) -j $(KERNEL_JSON) -b $(RING_BUF) -w $(BUS_WIDTH) -s $(STREAMS) -n $(N_CU) -r $(BLACKBOX) -i $(KERNEL_DIR) -o $(SRC_OUT_DIR)
olympus: $(KERNEL_JSON) $(KERNEL_DIR)
	mkdir -p "$(SRC_OUT_DIR)"
	$(OLYMPUS) $(KERNEL_MLIR) -b $(RING_BUF) -w $(BUS_WIDTH) -s $(STREAMS) -n $(N_CU) -r $(BLACKBOX) -i $(KERNEL_DIR) -o $(SRC_OUT_DIR)

hls: $(RES_OUT_DIR)/results/$(CU_NAME).xo

chw: $(RES_OUT_DIR)/results/$(CU_NAME)_$(N_CU)CU.xclbin

chost: $(RES_OUT_DIR)/results/RunHardware.exe

run: chw chost
	cd "$(RES_OUT_DIR)/results/"; source $(VITIS); source $(XILINX_XRT)/setup.sh; emconfigutil --platform $(PLATFORM)
ifeq ($(TARGET),hw)
	cd "$(RES_OUT_DIR)/results/"; source $(VITIS); source $(XILINX_XRT)/setup.sh; unset XCL_EMULATION_MODE; ./RunHardware.exe $(CU_NAME)_$(N_CU)CU.xclbin $(RUN_FLAGS) 2>&1 | tee -a $(LOG)
	#python3 $(CUR_DIR)/$(BOARD_TARGET_PATH)/power.py $(RES_OUT_DIR)/results/power_profile_$(PLATFORM).csv 2>&1 | tee -a $(LOG)
	#python3 $(CUR_DIR)/$(BOARD_TARGET_PATH)/collector.py $(RES_OUT_DIR)/results $(CU_NAME) 2>&1 | tee -a $(LOG)
else
	cd "$(RES_OUT_DIR)/results/"; source $(VITIS); source $(XILINX_XRT)/setup.sh; export XCL_EMULATION_MODE=$(TARGET); ./RunHardware.exe $(CU_NAME)_$(N_CU)CU.xclbin $(RUN_FLAGS) 2>&1 | tee -a $(LOG)
endif

results: 
ifeq ($(TARGET),hw)
	python3 $(CUR_DIR)/$(BOARD_TARGET_PATH)/power.py $(RES_OUT_DIR)/results/power_profile_$(PLATFORM).csv
	python3 $(CUR_DIR)/$(BOARD_TARGET_PATH)/collector.py $(RES_OUT_DIR)/results $(CU_NAME)
endif

############################## Cleaning Rules ##############################
# Cleaning stuff
clean_all:
	-rm -rf "$(RES_OUT_DIR)/results/*"

clean_hls: 
	-rm -rf $(RES_OUT_DIR)/results/$(CU_NAME).xo

clean_chw:
	-rm -rf $(RES_OUT_DIR)/results/$(CU_NAME)_$(N_CU)CU.xclbin

clean_chost:
	-rm -rf $(RES_OUT_DIR)/results/RunHardware.exe

distclean:
	-rm -rf $(RES_OUT_DIR)
