from backend.Backend import *
from backend.Vitis import *
from backend.cFDK import *

def backendGenerator(target, target_root):
    if target == "xilinx_u280_xdma_201920_3":
        return Vitis(target_root)
    elif target == "cloudFPGA":
        return cFDK(target_root)
    else:
        raise Exception("Unknown target platform:",target)
