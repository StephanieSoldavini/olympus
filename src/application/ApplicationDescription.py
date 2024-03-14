import json
import os

from xdsl.parser import Parser as IRParser
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, IntegerType
from xdsl.dialects.func import Func
from xdsl.ir import MLContext
from xdsl.utils.exceptions import VerifyException
from dialects.olympus import Olympus, KernelOp, ChannelOp, IndexOp

import cgen as c # TODO decouple

def parse_mlir(mlirdfg):
    ### Open MLIR ###
    if not mlirdfg:
        print("Please provide MLIR input file.")
        exit(1)
    ctx = MLContext()
    ctx.register_dialect(Arith)
    ctx.register_dialect(Builtin)
    ctx.register_dialect(Func)
    ctx.register_dialect(Olympus)
    #ctx.register_dialect(Dfg)
    ctx.allow_unregistered = True
    with open(mlirdfg) as f:
        parser = IRParser(ctx, f.read(), name=f"{mlirdfg}")
    return parser.parse_module()

def verify_mlir(module_op):
    ### Verify MLIR ###
    for operator in module_op.walk():
        try:
            operator.verify()
        except VerifyException as e:
            print()
            print(operator.name, " : ", operator)
            print("### ", e, " ###")
        except Exception as e:
            print()
            print("### ", e, " ###")

def mlir_type_to_c_type(mlir_type):
    if isinstance(mlir_type,IntegerType):
        retval = f"ap_uint<{mlir_type.width.data}>"
    else:
        print("Non-integers not supported") #TODO
        print(f"Type: {mlir_type}")
        exit(1)
    return retval

class Param:
    #def __init__(self, data_depth, param_type, data_width, direction):
    def __init__(self, operand, channel_name, direction):
        self.op = operand.op
        if self.op.scratch: # I know this is silly but it just being "true" but not even actually a string makes me nervous
            self.scratch = True
        else:
            self.scratch = False
        self.persistent = self.op.persistent
        self.channel_name = channel_name
        self.data_depth = self.op.depth.value.data
        self.param_type = str(self.op.paramType.data)
        self.data_width = self.op.data.type.parameters[0].width.data
        self.direction = direction
        self.bundle = None
        self.internal = None
        if self.param_type == "complex":
            self.data_type = "uint64_t"
        else:
            self.data_type = mlir_type_to_c_type(self.op.data.type.parameters[0])
        self.c_op = self.gen_c_op() # TODO I don't like including cgen in this file

    def inline(self):
        # This is only implemented for debug purposes so the cgen printer doesn't cry about Params in the file
        return f"[ERROR I SHOULDN'T BE HERE {self.c_op.name} {self.param_type}]"

    def gen_intf_pragmas(self):
        pragmas = c.Collection()
        if self.param_type == "complex":
            pragmas.append()

    def gen_c_op(self):
        c_op = c.Line("")
        if self.param_type == "small": #BRAM
            c_op = c.ArrayOf(c.Value(self.data_type, self.channel_name), self.data_depth)
        elif self.param_type == "stream": #FIFO
            #print("TODO: Stream not implemented")
            c_op = c.Value(f"hls::stream<{self.data_type}>&", self.channel_name)
        elif self.param_type == "complex": #AXI
            #print("TODO: Complex not implemented")
            c_op = c.Value(self.data_type, self.channel_name)
        else:
            print("Supported types are small, stream, complex")
        return c_op

    def __str__(self):
        return f"{self.c_op}, {self.data_depth}, {self.param_type}, {self.data_width}, {self.direction}, scr:{self.scratch}, internal:{self.internal}"


class ApplicationKernel:
    def __init__(self, operator, parent_network): 
        self.name = operator.callee.data#+"_krnl"
        self.sw_func = operator.callee.data
        self.parent_network = parent_network
        self.uses = set() # kernels who produce input for us
        self.users = set() # kernels who consume output from us
        param_id = 0
    
        self.total_size = None

        self.read_func = None
        self.in_ptrs = None
        self.read_streams = None

        self.write_func = None
        self.out_ptrs = None
        self.write_streams = None

        self.bram_in_func = None
        self.in_bufs = None
        self.bram_out_func = None
        self.out_bufs = None

        self.stream_io = None

        self.base_ptr = None
        self.base_msbs = None
        self.axi_io = None
        self.addrtrans_func = None
        self.kernel_offsets = None

        self.start_func = None
        self.start_toks = None
        self.done_func = None
        self.done_toks = None

        #print(self.name)
        #print("op inputs:",  [x.name_hint for x in operator.inputs ])
        #print("op outputs:", [x.name_hint for x in operator.outputs])
        #print("op inouts:",  [x.name_hint for x in operator.inouts ])
        self.parameters = {}
        for inp in operator.inputs:
            if isinstance(inp.op, ChannelOp):
                self.process_param(inp, operator, param_id, "in")
                param_id += 1
            elif isinstance(inp.op, IndexOp):
                print("index")
            else:
                print("ERROR: Input not channel or index:", inp)
                exit(1)
        for outp in operator.outputs:
            self.process_param(outp, operator, param_id, "out")
            param_id += 1
        for iop in operator.inouts:
            self.process_param(iop, operator, param_id, "inout")
            param_id += 1
        if self.get_axi_io():
            self.bundles = {}
            self.find_bundles()
        else:
            print("NO AXI")

    def __str__(self):
        return f"{self.name}"

    def find_bundles(self):
        # Ask the bambu or vitis hls synthesis reports for the bundle situation
        # TODO
        # { "bundle name" : [list of param names]}
        if self.name == "kernelX":
            #self.bundles = {"gmem0" : ["ix_C", "x_K", "ex_M"]} # TODO get this from the paths buried in the op
            self.bundles = {"gmem0" : ["ix_C", "ex_M"]} # TODO get this from the paths buried in the op
        elif self.name == "kernelY":
            #self.bundles = {"gmem1" : ["x_K", "ox_F", "ex_O", "iox_H"]}
            self.bundles = {"gmem1" : [ "ox_F", "ex_O"]}
        elif self.name == "taumol_sw_top":
            self.bundles = {"gmem0" : ["k_maj"], "gmem1" : ["tau_g"], "gmem2" : ["tau_r"]}
        elif self.name == "kernel_projection":
            self.bundles = {"common" : ["kernel_projection_0", "kernel_projection_1", "kernel_projection_2"]}
        elif self.name == "kernel_viterbi":
            self.bundles = {"common" : ["kernel_viterbi_0", "kernel_viterbi_1", "kernel_viterbi_2"]}
        elif self.name == "helmholtz":
            self.bundles = {"gmem0" : ["S", "u", "D"], "gmem1" : ["v"]}
        else: 
            print(f"ERROR: Missing bundle mapping for kernel: {self.name}")
            exit()
        for b in self.bundles:
            for p in self.bundles[b]:
                self.parameters[p].bundle = b

    def process_param(self, io, operator, param_id, direction):
        channel_name = io.name_hint
        if (not channel_name):
            channel_name = operator.callee.data + "_" + str(param_id)
        param = Param(io, channel_name, direction)
        #print(io)
        for i in io.uses:
            if isinstance(i.operation, KernelOp):
                if i.operation.callee.data != self.name:
                    if direction == "out":
                        self.users.add(i.operation.callee.data)
                    elif direction == "in":
                        self.uses.add(i.operation.callee.data)
                    else:
                        print("ERROR: Dependency on inout")
            else:
                print("NOT A KERNEL OP")

        self.parameters[channel_name] = param
        #print("ADDED PARAM:", param.channel_name, param.direction)
        param_id += 1
        if param.op in self.parent_network.externals:
            param.internal = False
            stored = self.parent_network.externals[param.op]
            #print(f"match: param.direction: {param.direction}, stored: {stored}, {stored.direction}")
            if param.direction == "out" and stored.direction == "in":
                src = param
                sink = stored
            elif param.direction == "in" and stored.direction == "out":
                src = stored
                sink = param
            else:
                print("ERROR: Bidirectional internal port mismatch.")
        
            param.internal = True
            stored.internal = True
            self.parent_network.internals[param.op] = (src, sink)
            del self.parent_network.externals[param.op]

        elif param.scratch:
            param.internal = True
            self.parent_network.internals[param.op] = (param, param)
        else:
            param.internal = False
            self.parent_network.externals[param.op] = param

    def get_inputs(self):
        try: 
            self._inputs
        except AttributeError:
            self._inputs = [x for (k,x) in self.parameters.items() if x.direction=="in"]
        return self._inputs

    def get_outputs(self):
        try: 
            self._outputs
        except AttributeError:
            self._outputs = [x for (k,x) in self.parameters.items() if x.direction=="out"]
        return self._outputs
    
    def get_inouts(self):
        try: 
            self._inouts
        except AttributeError:
            self._inouts = [x for (k,x) in self.parameters.items() if x.direction=="inout"]
        return self._inouts

    def get_params_of_dir(self, d):
        if d == "in":
            return self.get_inputs()
        elif d == "out":
            return self.get_outputs()
        elif d == "inout":
            return self.get_inouts()
        else:
            print(f"ERROR: Direction '{d}' invalid")
            return None

    def get_axi_io(self):
        try: 
            self._axi_io
        except AttributeError:
            self._axi_io = [x for (k,x) in self.parameters.items() if x.param_type=="complex"]
        return self._axi_io

    def get_stream_io(self):
        try: 
            self._stream_io
        except AttributeError:
            self._stream_io = [x for (k,x) in self.parameters.items() if x.param_type=="stream"]
        return self._stream_io

    def get_stream_inputs(self):
        try: 
            self._stream_inputs
        except AttributeError:
            self._stream_inputs = [x for x in self.get_stream_io() if x.direction=="in"]
        return self._stream_inputs

    def get_stream_outputs(self):
        try: 
            self._stream_outputs
        except AttributeError:
            self._stream_outputs = [x for x in self.get_stream_io() if x.direction=="out"]
        return self._stream_outputs

    def get_bram_io(self):
        try: 
            self._bram_io
        except AttributeError:
            self._bram_io = [x for (k,x) in self.parameters.items() if x.param_type=="small"]
        return self._bram_io

    def get_bram_inputs(self):
        try: 
            self._bram_inputs
        except AttributeError:
            self._bram_inputs = [x for x in self.get_bram_io() if x.direction=="in"]
        return self._bram_inputs

    def get_bram_outputs(self):
        try: 
            self._bram_outputs
        except AttributeError:
            self._bram_outputs = [x for x in self.get_bram_io() if x.direction=="out"]
        return self._bram_outputs

    def get_non_axi_io(self):
        try: 
            self._non_axi_io
        except AttributeError:
            self._non_axi_io = self.get_bram_io() + self.get_stream_io()
        return self._non_axi_io

    def has_non_axi_of_dir(self, d):
        for x in self.get_non_axi_io():
            if x.direction == d and x.scratch == False and x.op in self.parent_network.externals:
                return True
        return False


class ApplicationNetwork:
    def __init__(self, name):
        self.name = name
        self.kernels = []
        self.internals = {} # { channelOp : ( src Param, sink Param ) }
        self.externals = {} # { channelOp : Param }
        # TODO collect which IO are outward facing

    def __str__(self):
        buf = F""".:: Application network name: {self.name} ::.
        Number of kernels  = {len(self.kernels)}\n"""
        #for k in self.networks:
        #    buf += '\n'
        #    buf += " - "
        #    buf += str(k)
        buf += "### INTERNALS: ###\n"
        for x in self.internals:
            buf += (f"\t{x}\n")
            y = self.internals[x]
            buf += (f"\t\tsrc:  {y[0]}\n")
            buf += (f"\t\tsink: {y[1]}\n")
        buf += (f"### EXTERNALS: ###\n")
        for x in self.externals:
            buf += (f"\t{x}\n")
            y = self.externals[x]
            buf += (f"\t\tparam:  {y}\n")
        return buf

    def add_kernel(self, operator):
        self.kernels.append(ApplicationKernel(operator, self))

class ApplicationDescription:

    def __init__(self, name, mlirdfg): 
        self.name = name
        self.networks = {} # netname (str) : ApplicationNetwork
        module_op = parse_mlir(mlirdfg)
        verify_mlir(module_op)

        ### Collect Olympus Nodes (TODO: Asuming only one rn) ###
        for operator in module_op.walk():
            if isinstance(operator, KernelOp):
                ## TODO joined networks will have the same func.func parent, 
                ## disjoint networks need different CUs
                network_name = operator.parent_op().sym_name
                if network_name not in self.networks:
                    self.networks[network_name] = ApplicationNetwork(network_name)
                self.networks[network_name].add_kernel(operator)


        for netname in self.networks:
            net = self.networks[netname]
            print(net)
#            print(f"### NET: {netname} ###")
#            print(f"### INTERNALS: ###")
#            for x in net.internals:
#                print(f"\t{x}")
#                y = net.internals[x]
#                print(f"\t\tsrc:  {y[0]}")
#                print(f"\t\tsink: {y[1]}")
#            print(f"### EXTERNALS: ###")
#            for x in net.externals:
#                print(f"\t{x}")
#                y = net.externals[x]
#                print(f"\t\tparam:  {y}")

    def __str__(self):
        buf = F""".:: Application name: {self.name} ::.
        Number of networks = {len(self.networks)}"""
        for k in self.networks:
            buf += '\n'
            buf += " - "
            buf += str(k)
        return buf
#    def print(self):
#        print(".:: Application name:",self.name,"::.")
#        print("Number of kernels =",len(self.kernels))
#        for k in self.kernels:
#            print(" - ", end='')
#            k.print()

