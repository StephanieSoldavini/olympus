VITIS=/opt/xilinx/Vitis/2021.1

OPATH=../../src
OUT=out
${OPATH}/olympus.py -p ${OPATH}/targetplatform/alveo/alveo_u280.json -a ./helmholtz.mlir -o $OUT
if [ $? -eq 0 ]; then
    source $VITIS/settings64.sh
    vitis_hls ${OPATH}/scripts/omm_hls.tcl $OUT/src/helm_top_CU.cpp
fi
