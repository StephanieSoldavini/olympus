import cgen as c
from collections import defaultdict
from math import log, ceil
import re
from copy import deepcopy
import os

from application import Param 

dirs = ["in", "out", "inout"]

def flatten_2D_array(arr):
    return [i for p in arr for i in p]

def c_type_width(c_type):
    if "double" in c_type:
        return 64
    elif "float" in c_type:
        return 32
    else:
        m = re.findall(r'\d+', c_type)
        if len(m) > 0:
            return int(m[0])
        else:
            if "short" in c_type or "int" in c_type or "long" in c_type:
                print("ERROR: Ambiguous bitwidth type: " + c_type + ". Please use stdint or ap_int types.")
            else:
                print("ERROR: Unable to determine size of datatype:", c_type)
            return -1

def value_rename(val, name):
    if isinstance(val, c.Value):
        return c.Value(val.typename, name)
    elif isinstance(val, c.NestedDeclarator):
        newval = deepcopy(val)
        newval.subdecl = value_rename(newval.subdecl, name)
        return newval
    else:
        print(f"ERROR: Unexpected item in bagging area. {val} not Value or NestedDecl")

def streamify(val):
    if isinstance(val, c.NestedDeclarator):
        return streamify(val.subdecl)
    if "stream" in val.typename:
        return val
    return c.Value(f"hls::stream<{val.typename}>&", val.name)

def get_type(var, strip_stream=False):
    if isinstance(var, c.Value):
        typename = var.typename
    elif isinstance(var, c.NestedDeclarator):
        typename = get_type(var.subdecl)
    elif isinstance(var, Param):
        typename = get_type(var.c_op)
    else:
        print("ERROR: Cannot get type of var:", var)
        return None
    if strip_stream:
        m = re.match("(?:hls::)?stream<([\w<>]*)>&", typename)
        if m:
            return m.group(1)
        else:
            return typename
    else:
        return typename
    
class CUGen:
    #cu_file = None

    def __init__(self, olympusCtx):
        self.oCtx = olympusCtx
        self.fixed_point = True # TODO ... does this come from somewhere or is it always true
        self.streams = True # TODO should always be true

        # TODO SHOULD COME FROM self.oCtx.target
        self.bus_width = 128
        print(f"NOTE: BUS WIDTH IS SET TO {self.bus_width}")
        self.bus_type = f"ap_uint<{self.bus_width}>"
        self.channel_size = 512*1024*1024

        self.ring_buf = 1 # TODO
        self.ring_buf = self.ring_buf if (self.ring_buf > 0) else 1 # force a value below 1 to be 1
        if self.ring_buf > 1:
            self.ring_buf_flag = c.Value("unsigned int", "flag")
        
        self.loop_counter = c.Value("unsigned int", "count") 
        for netname in self.oCtx.application.networks:
            intl = self.bus_width
            network = self.oCtx.application.networks[netname]
            for k in network.kernels:
                #max_data_width = max([x.data_width for (key,x) in k.parameters.items()])
                if k.get_non_axi_io():
                    max_data_width = max([x.data_width for x in k.get_non_axi_io()])
                else:
                    max_data_width = 64
                print("maxdw =", max_data_width)
                # TODO vvv inefficient, change using multiplicity? iris?
                intl = min(intl, int(self.bus_width / max_data_width))

            omm_file = self.gen_omm(netname, network, intl)

            fname = self.oCtx.outdir+f"/src/{netname.data}_CU.cpp"
            with open(fname, 'w') as cf:
                cf.write(str(omm_file))
            os.system(f"/opt/archive/llvm-bin/llvm-bin/bin/clang-format -style=llvm -i {fname}")
        
    def call_func(self, func, arg_list, with_semicolon=True):
        strbuf = ""
        for arg in arg_list:
            if isinstance(arg, str):
                strbuf += f"{arg}" 
            elif isinstance(arg, c.Value):
                strbuf += f"{arg.name}" 
            elif isinstance(arg, c.NestedDeclarator):
                strbuf += f"{arg.name}"
            elif isinstance(arg, Param):
                strbuf += f"{arg.c_op.name}"
            else:
                print(f"ERROR: Unexpected type for arg: {arg}")
            strbuf += ", "

        strbuf = strbuf[:-2] # remove trailing comma and space
        if isinstance(func, str):
            fname = func
        elif isinstance(func, c.FunctionDeclaration):
            fname = func.name
        else:
            fname = func.fdecl.name
        if with_semicolon:
            return c.Statement(f"{fname}({strbuf})")
        else:
            return c.Line(f"{fname}({strbuf})")

    def gen_datamover(self, kname, read_nwrite, device_args, intl):
        if read_nwrite:
            func_name = f"{kname}_read_data"
            host_args_name = "in"
        else:
            func_name = f"{kname}_write_data"
            host_args_name = "out"
        if self.ring_buf > 1:
            host_args = [c.Pointer(c.Value(self.bus_type, host_args_name + "_rb" + str(i))) 
                    for i in range(self.ring_buf)]
        else:
            host_args = [c.Pointer(c.Value(self.bus_type, host_args_name))] 


        func_args = []

        stream_args = []
        for i in range(intl):
            stream_args.extend([streamify(c.Value(get_type(arg.c_op), arg.c_op.name + str(i))) for arg in device_args])
        print("Stream args:", [x.inline() for x in stream_args])
        func_args = host_args + stream_args
        func_args.append(self.loop_counter)
        if self.ring_buf > 1:
            func_args.append(self.ring_buf_flag)
        func_decl = c.FunctionDeclaration(c.Value("void", func_name), func_args)
        func_body = c.Block()
        if self.ring_buf > 1:
            buf_list = ["_rb" + str(i) for i in range(self.ring_buf)]
        else: 
            buf_list = [""]

        data_type = get_type(device_args[0].c_op, strip_stream=True) # TODO make data width dynamic by arg
        sizeof = c_type_width(data_type) 
        data_member = ""
        axi_member = ""
        if data_type in ["float", "double"]:
            union = c.Value("union pkt",   # TODO fix this indentation??
                    c.Block([
                        c.Value(data_type, "data"), 
                        c.Value(f"uint{sizeof}_t", "axi_data") # TODO must be a regular C type length
                        ])
                    )
            data_member = ".data"
            axi_member = ".axi_data"
            func_body.append(union)
            obj_type = "pkt"
        else:
            obj_type = data_type
        elem = c.Value(self.bus_type, "elem") 
        func_body.append(elem) 
        for i in range(intl):
            func_body.append(c.Value(obj_type, f"obj{i}")) 
        data_move_collection = []
        for i in range(self.ring_buf):
            data_move_collection.append(c.Collection())
            totalSize = 0
            for arg in device_args:
                argcount = arg.data_depth
                totalSize += argcount
            prevTot = 0
            for arg in device_args:
                device_arg = arg.c_op.name
                host_arg = f"&{host_args[i].name}[{totalSize}*{self.loop_counter.name}+{prevTot}]" 
                prevTot += arg.data_depth
                size = f"{arg.data_depth}*sizeof({get_type(arg)})"
                for_body = c.Block()
                for_body.append(c.Pragma("HLS pipeline II=1"))
                loop_counter = c.Value("unsigned int", "num")
                host_arg = host_arg[1:-1]+"+num]"
                if read_nwrite:
                    for_body.append(c.Assign(elem.name, host_arg))
                    for n in range(intl):
                        for_body.append(c.Assign(f"obj{n}{axi_member}", f"{elem.name}.range({(n+1)*sizeof-1},{n*sizeof})"))
                    for n in range(intl):
                        for_body.append(c.Statement(f"{device_arg}{n} << obj{n}"))
                else:
                    for n in range(intl):
                        for_body.append(c.Statement(f"{device_arg}{n} >> obj{n}{data_member}"))
                    for n in range(intl):
                        for_body.append(c.Assign(f"{elem.name}.range({(n+1)*sizeof-1},{n*sizeof})", f"obj{n}{axi_member}"))
                    for_body.append(c.Assign(host_arg, elem.name))

                for_loop = c.For(f"{loop_counter.inline()} = 0", f"{loop_counter.name} < {arg.data_depth}", f"{loop_counter.name}++", for_body)
                data_move_collection[i].append(for_loop)
        if self.ring_buf > 1:
            else_collection = c.Block(data_move_collection[-1])
            for i in range(self.ring_buf-2, -1, -1):
                else_collection = c.If(f"{self.ring_buf_flag.name} == {i}", c.Block(data_move_collection[i]), else_collection)
            func_body.append(else_collection)
        else:
            func_body.append(data_move_collection[0])

        return c.FunctionBody(func_decl, func_body), host_args, stream_args

    def _omm_includes(self, cu_file):
        cu_file.append(c.Include("string.h", system=True))
        cu_file.append(c.Include("stdio.h", system=True))
        cu_file.append(c.Include("ap_int.h", system=True))
        cu_file.append(c.Include("stdint.h", system=True))
        if self.streams:
            cu_file.append(c.Include("hls_stream.h", system=True))
        if self.fixed_point:
            cu_file.append(c.Include("ap_fixed.h", system=True))

    def _gen_kernel_axi_ptrs(self, k):
        k_ptrs = defaultdict(list)
        for d in dirs:
            if k.has_non_axi_of_dir(d):
                k_ptrs[d].append(c.Pointer(c.Value(self.bus_type, k.name+d))) 
        for p in k.get_axi_io():
            if p.bundle != None:
                # TODO care if there are only in/out AXI ports
                k_ptrs["inout"].append(c.Pointer(c.Value(self.bus_type, k.name+"_base")))
                break


        return k_ptrs

    def _omm_mem_ptrs(self, network):
        """ Generate the AXI ports
        This is where we concretize how many channels to use
        Channels for Olympus-controlled AXI
        Channels for Kernel-controlled AXI

        TODO: Currently only using 1 channel for in-direction and 1 for out-direction
        """
        # - HBM pointers

        kernel_ptrs = defaultdict(list)
        for k in network.kernels:
            k_ptrs = self._gen_kernel_axi_ptrs(k)
            for d in dirs:
                kernel_ptrs[d].extend(k_ptrs[d])
            
        ptrs = defaultdict(list)
        if self.ring_buf > 1:
            for d in dirs:
                for arg in kernel_ptrs[d]:
                    if self.ring_buf > 1:
                        ptrs[d].extend(
                                [c.Pointer(c.Value(get_type(arg), arg.name + "_rb" + str(i))) 
                                    for i in range(self.ring_buf)]
                                )
                    else:
                        ptrs[d].append( c.Pointer(c.Value(get_type(arg), f"{arg.name}")) )
        else:
            for d in dirs:
                for arg in kernel_ptrs[d]:
                    ptrs[k].append(c.Pointer(c.Value(get_type(arg), arg.name)))
        mem_ptrs = ptrs 

        return mem_ptrs

    def _omm_intf_pragmas(self, network, intl):
        mem_ptrs = self._omm_mem_ptrs(network)

        interface_pragmas = c.Collection()

        n = 0 
        mem_ptrs_flat = []
        for d in mem_ptrs:
            mem_ptrs_flat.extend(mem_ptrs[d])
        for arg in mem_ptrs_flat:
            interface_pragmas.append(c.Pragma(f"HLS INTERFACE m_axi port={arg.name} offset=slave bundle=gmem{n}"))
            interface_pragmas.append(c.Pragma(f"HLS INTERFACE s_axilite port={arg.name} bundle=control"))
            n = n + 1

        # - Control (num_times / rb flag)
        control_args = [c.Const(c.Value("unsigned int", "num_times"))]
        if self.ring_buf > 1:
            control_args.append(self.ring_buf_flag)

        for arg in control_args:
            interface_pragmas.append(c.Pragma(f"HLS INTERFACE s_axilite port={arg.name} bundle=control"))
        interface_pragmas.append(c.Pragma(f"HLS INTERFACE s_axilite port=return bundle=control"))

        # - Start / done streams
        startdone_streams = []
        for j in range(intl):
            for k in network.kernels:
                startdone_streams.append(c.Value("hls::stream<ap_uint<1>>&", f"{k.name}_kernel_start{j}"))
                startdone_streams.append(c.Value("hls::stream<ap_uint<1>>&", f"{k.name}_kernel_done{j}"))
                interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=axis register_mode=off port={k.name}_kernel_start{j}"))
                interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=axis register_mode=off port={k.name}_kernel_done{j}"))

        # - IO to kernel
        kernel_args = set()
        kernel_args.update([x for (k,x) in network.externals.items()])
        for k in network.kernels:
            kernel_args.update(k.get_axi_io())

        kernel_io = []
        for arg in kernel_args:            
            if arg.param_type == "complex":
                kernel_io.append(c.Value(get_type(arg.c_op), f"{arg.c_op.name}"))
                interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=s_axilite port={arg.c_op.name} bundle=control"))
            for i in range(intl):
                if arg.param_type == "small": # bram plm
                    kernel_io.append(c.ArrayOf(c.Value(get_type(arg.c_op), f"{arg.c_op.name}_buf{i}"), arg.data_depth))
                    interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=ap_memory port={arg.c_op.name}_buf{i} storage_type=ram_1p"))
                elif arg.param_type == "stream": # axis
                    kernel_io.append(c.Value(f"{get_type(arg.c_op)}", f"{arg.c_op.name}{i}"))
                    interface_pragmas.append(c.Pragma(f"HLS STREAM variable={arg.c_op.name}{i} depth={arg.data_depth}"))
                elif arg.param_type == "complex": #m axi
                    kernel_io.append(c.Pointer(c.Value(get_type(arg.c_op), f"{arg.c_op.name}_kernel{i}")))
                    interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=ap_none port={arg.c_op.name}_kernel{i}"))

        arglist = mem_ptrs_flat + control_args + startdone_streams + kernel_io

        return interface_pragmas, arglist, kernel_args

    def _omm_cu_wrapper_func_body(self):
        pass

    def _omm_numtimes_loop(self):
        pass

    def gen_stream_to_bram(self, kname, in_nout, args):
        if in_nout:
            func_name = f"{kname}_in_bram"
        else:
            func_name = f"{kname}_out_bram"
        func_args = [streamify(a.c_op) for a in args] 
        bram_bufs = []
        for arg in args:
            if arg.param_type != "stream" and self.streams:
                bram_bufs.append(c.ArrayOf(c.Value(get_type(arg.c_op, strip_stream=True), f"{arg.c_op.name}_buf"), 
                arg.data_depth))
        func_args.extend(bram_bufs)
        if in_nout:
            done_token = c.Value("hls::stream<ap_uint<1>>&", "done_token") 
            func_args.append(done_token)
        else:
            start_token = c.Value("hls::stream<ap_uint<1>>&", "start_token")
            func_args.append(start_token)

        func_decl = c.FunctionDeclaration(c.Value("void", func_name), func_args)
        func_body = c.Block()
        if not in_nout:
            func_body.append(c.Statement(f"{start_token.name}.read()"))

        loopvar = c.Value("unsigned int", "i")
        for i in args:
            if i.param_type != "stream":
                if in_nout:
                    buf = c.Statement(f"{i.c_op.name} >> {i.c_op.name}_buf[{loopvar.name}]")
                else:
                    buf = c.Statement(f"{i.c_op.name} << {i.c_op.name}_buf[{loopvar.name}]")
                for_body = c.Block([ c.Pragma("HLS pipeline II=1"), buf ])
                for_loop = c.For(f"{loopvar.inline()} = 0", f"{loopvar.name} < {i.data_depth}", f"{loopvar.name}++", for_body)
                func_body.append(for_loop)
        krnl_args = []
        for a in args:
            if a.param_type != "stream" and self.streams:
                krnl_args.append(f"{a.c_op.name}_buf")
            else:
                krnl_args.append(a.c_op.name)
        if in_nout:
            func_body.append(c.Statement(f"{done_token.name}.write(1)"))
        return c.FunctionBody(func_decl, func_body), bram_bufs


    def gen_addrtrans(self, kname, base, io, intl):
        total_size_buf = ""
        for x in io:
            total_size_buf += f"{ceil((x.data_width*x.data_depth)/8)} + "
        total_size = c.Define(f"TOTAL_SIZE_{kname}", f"({total_size_buf[:-2]})")
        func_name = f"{kname}_{base.name}_addrtrans"
        func_args = []
        # count
        func_args.append(self.loop_counter)
        # offset inputs
        func_args.extend([c.Const(c.Value(x.data_type, x.channel_name)) for x in io if x.internal == False])
        # base addr
        func_args.append(base)
        # translated offset outputs
        offsets_to_kernel = [c.Pointer(c.Value(x.data_type, f"{x.channel_name}_kernel")) for x in io]
        all_offsets = [value_rename(x, f"{x.name}{i}") for i in range(intl) for x in offsets_to_kernel]
        func_args.extend(all_offsets)
        # base_msbs
        base_width = 64
        n_lsbs = int(log(self.channel_size,2))
        n_msbs = base_width - n_lsbs
        base_msbs = c.Pointer(c.Value(f"ap_uint<{n_msbs}>", f"base_msbs"))
        func_args.append(base_msbs)
        # done token
        done_writes = []
        for i in range(intl):
            done_token = c.Value("hls::stream<ap_uint<1>>&", f"done_token{i}") 
            func_args.append(done_token)
            done_writes.append(c.Statement(f"{done_token.name}.write(1)"))
        
        func_decl = c.FunctionDeclaration(c.Value("void", func_name), func_args)
        func_body = c.Block()
        
        ptr_t = "ptr"
        union = c.Value(f"union {ptr_t}",   
                c.Block([ c.Value("uint64_t", "uint"), 
                          c.Pointer(c.Value("uint64_t", "uint_ptr"))]))
        func_body.append(union)

        base_ptr = c.Value(ptr_t, f"{base.name}_ptr")
        func_body.append(base_ptr)
        base_mod_ptr = c.Value(ptr_t, f"{base.name}_mod_ptr")
        func_body.append(base_mod_ptr)
        func_body.append(c.Assign(f"{base_ptr.name}.uint_ptr", f"(uint64_t*)({base.name}->to_long())"))
        base_bits = c.Value(f"ap_uint<{base_width}>", f"{base.name}_bits")
        func_body.append(c.Assign(base_bits.inline(), f"(uint64_t){base_ptr.name}.uint"))
        func_body.append(c.Assign(f"{base_mod_ptr.name}.uint", f"{base_bits.name}.range({n_lsbs-1},0).to_long()"))
        base_mod = c.Pointer(c.Value("uint64_t", f"{base.name}_mod")) #TODO width
        func_body.append(c.Assign(base_mod.inline(), f"{base_mod_ptr.name}.uint_ptr"))
        func_body.append(c.Assign(f"*{base_msbs.name}", f"{base_bits.name}.range({base_width-1},{n_lsbs})"))

        for i in range(intl):
            for arg in io:
                io_ptr = c.Value(ptr_t, f"{arg.channel_name}_ptr{i}")
                func_body.append(io_ptr)
                func_body.append(c.Assign(f"{io_ptr.name}.uint_ptr", 
                    f"(uint64_t*)(&(((uint8_t*){base_mod.name}+(({intl}*{self.loop_counter.name}+{i})*({total_size.symbol})))[{arg.channel_name}]))"))
                func_body.append(c.Assign(f"*{arg.channel_name}_kernel{i}", f"{io_ptr.name}.uint"))
    
        func_body.extend(done_writes)

        return c.FunctionBody(func_decl, func_body), offsets_to_kernel, base_msbs, total_size

    def gen_start_func(self, k):
        func_name = f"{k.name}_start_func"
        args = []

        # Token from addrtrans
        if k.get_axi_io(): 
            start_at_token = c.Value("hls::stream<ap_uint<1>>&", "at_start_token")
            args.append(start_at_token)

        # Token from bram writer 
        start_token = c.Value("hls::stream<ap_uint<1>>&", "start_token")
        args.append(start_token)

        # Tokens to wait on other kernels
        uses_start_tokens = []
        for u in k.uses:
            uses_start_tokens.append(c.Value("hls::stream<ap_uint<1>>&", f"{u}_start_token"))
        args.extend(uses_start_tokens)

        # Token saying this function is done (send to done func)
        done_token = c.Value("hls::stream<ap_uint<1>>&", "done_token")
        args.append(done_token)

        # Token to start kernel
        kernel_start = c.Value("hls::stream<ap_uint<1>>&", "kernel_start")
        args.append(kernel_start)

        token = c.Value("ap_uint<1>", "token")
        func_decl = c.FunctionDeclaration(c.Value("void", func_name), args)
        func_body = c.Block()
        func_body.append(c.Pragma("HLS inline off"))
        func_body.append(token)
        func_body.append(c.Assign(token.name, c.Line(f"{start_token.name}.read()")))
        if k.get_axi_io(): 
            func_body.append(c.Assign(token.name, c.Line(f"{start_at_token.name}.read()")))
        for u in uses_start_tokens:
            func_body.append(c.Assign(token.name, c.Line(f"{u.name}.read()")))

        func_body.append(c.Statement(f"{kernel_start.name}.write(1)"))
        func_body.append(c.Statement(f"{done_token.name}.write({token.name})"))
        return c.FunctionBody(func_decl, func_body),  uses_start_tokens

    def gen_done_func(self, k):
        func_name = f"{k.name}_done_func"
        # Kernel has finished
        kernel_done = c.Value("hls::stream<ap_uint<1>>&", "kernel_done")
        # Waiting on start_func
        start_token = c.Value("hls::stream<ap_uint<1>>&", "start_token")
        # This module is finished (send to bram mover)
        done_token = c.Value("hls::stream<ap_uint<1>>&", "done_token")
        # This kernel is done, let followers start
        users_done_tokens = []
        for u in k.users:
            users_done_tokens.append(c.Value("hls::stream<ap_uint<1>>&", f"{u}_done_token"))

        args = [kernel_done, start_token, done_token]
        args.extend(users_done_tokens)
        token = c.Value("ap_uint<1>", "token")
        func_decl = c.FunctionDeclaration(c.Value("void", func_name), args)
        func_body = c.Block()
        func_body.append(c.Pragma("HLS inline off"))
        func_body.append(c.Assign(token.inline(with_semicolon=False), c.Line(f"{start_token.name}.read()")))
        func_body.append(c.Assign(c.Value(get_type(kernel_done, strip_stream=True), "tmp").inline(with_semicolon=False), c.Line(f"{kernel_done.name}.read()")))
        func_body.append(c.Statement(f"{done_token.name}.write({token.name})"))

        for u in users_done_tokens:
            func_body.append(c.Statement(f"{u.name}.write({token.name})"))
        return c.FunctionBody(func_decl, func_body), users_done_tokens

    def _omm_kernel_driver(self, k, intl):
        # BRAM and Stream io need READ/WRITE modules
        # TODO disallowing BRAM inout
        func_body = c.Block()
        func_body.append(c.Pragma("HLS inline"))
        bram_stream_in = k.get_bram_inputs() + k.get_stream_inputs()
        bram_stream_in = [x for x in bram_stream_in if x.internal == False]
        read_func = None
        in_ptrs = []
        if bram_stream_in:
            read_func, in_ptrs, read_streams = self.gen_datamover(k.name, True, bram_stream_in, intl)
            k.read_func = read_func
            k.in_ptrs = in_ptrs
            k.read_streams = read_streams

        bram_stream_out = k.get_bram_outputs() + k.get_stream_outputs()
        bram_stream_out = [x for x in bram_stream_out if x.internal == False]
        write_func = None
        out_ptrs = []
        if bram_stream_out:
            write_func, out_ptrs, write_streams = self.gen_datamover(k.name, False, bram_stream_out, intl)
            k.write_func = write_func
            k.out_ptrs = out_ptrs
            k.write_streams = write_streams

        stream_i = [x.c_op for x in k.get_stream_inputs() if x.internal == False]
        stream_o = [x.c_op for x in k.get_stream_outputs() if x.internal == False]
        stream_io = stream_i + stream_o
        k.stream_io = stream_io

        # BRAM io need stream->bram loader
        bram_in = [x for x in k.get_bram_inputs() if x.internal == False]
        bram_in_streams = [streamify(x.c_op) for x in bram_in]
        bram_in_streams_noref = [c.Value(x.typename[:-1], f"{x.name}{i}") for x in bram_in_streams for i in range(intl)]
        func_body.extend(bram_in_streams_noref)
        bram_in_func, in_bufs = self.gen_stream_to_bram(k.name, True, bram_in)
        k.bram_in_func = bram_in_func
        k.in_bufs = in_bufs
        bram_out = [x for x in k.get_bram_outputs() if x.internal == False]
        bram_out_streams = [streamify(x.c_op) for x in bram_out]
        bram_out_streams_noref = [c.Value(x.typename[:-1], f"{x.name}{i}") for x in bram_out_streams for i in range(intl)]
        func_body.extend(bram_out_streams_noref)
        bram_out_func, out_bufs = self.gen_stream_to_bram(k.name, False, bram_out)
        k.bram_out_func = bram_out_func
        k.out_bufs = out_bufs

        # AXI io need AddrTrans
        axi_io = [x.c_op for x in k.get_axi_io() if x.internal == False]
        k.axi_io = axi_io
        if k.axi_io:
            base_ptr = c.Pointer(c.Value(self.bus_type, f"{k.name}_base"))
            k.base_ptr = base_ptr
            addrtrans_func, kernel_offsets, k.base_msbs, k.total_size = self.gen_addrtrans(k.name, base_ptr, [x for x in k.get_axi_io() if x.internal == False], intl)
            k.addrtrans_func = addrtrans_func
            k.kernel_offsets = kernel_offsets

        # Start / Finish modules
        start_func, start_toks = self.gen_start_func(k)
        k.start_func = start_func
        k.start_toks = start_toks
        done_func, done_toks = self.gen_done_func(k)
        k.done_func = done_func
        k.done_toks = done_toks

        func_name = f"{k.name}_driver"
        args = in_ptrs + out_ptrs 
        if k.axi_io:
            args += [base_ptr] + axi_io
            args += [value_rename(x, f"{x.name}{i}") for i in range(intl) for x in kernel_offsets]
            args += [k.base_msbs]
        args += [value_rename(x, f"{x.name}{i}") for x in stream_io for i in range(intl)]
        args += [value_rename(x, f"{x.name}{i}") for x in in_bufs   for i in range(intl)]
        args += [value_rename(x, f"{x.name}{i}") for x in out_bufs  for i in range(intl)]
        args += [c.Value("hls::stream<ap_uint<1>>&", f"kernel_start{i}") for i in range(intl)]
        args += [c.Value("hls::stream<ap_uint<1>>&", f"kernel_done{i}") for i in range(intl)]
        args += [value_rename(x, f"{x.name}{i}") for x in start_toks for i in range(intl)]
        args += [value_rename(x, f"{x.name}{i}") for x in done_toks  for i in range(intl)]
        args.append(self.loop_counter)
        if self.ring_buf > 1:
            args.append(self.ring_buf_flag)

        func_decl = c.FunctionDeclaration(c.Value("inline void", func_name), args)
        func_calls = []
        functions = set()
        if read_func:
            func_args = in_ptrs + read_streams
            func_args.append(self.loop_counter)
            if self.ring_buf > 1:
                func_args.append(self.ring_buf_flag)
            func_calls.append(self.call_func(read_func, func_args))
            functions.add(read_func)


        func_args = [self.loop_counter]
        if k.axi_io:
            func_args.extend(k.axi_io)
            func_args.append(k.base_ptr)
            for i in range(intl):
                func_args.extend([value_rename(x, f"{x.name}{i}") for x in k.kernel_offsets])
            func_args.append(k.base_msbs)
        at_toks = []
        for i in range(intl):
            at_tok = c.Value("hls::stream<ap_uint<1>>", f"tokenAT{i}")
            func_args.append(at_tok)
            func_body.append(at_tok)

        if k.axi_io:
            func_calls.append(self.call_func(addrtrans_func, func_args))
            functions.add(addrtrans_func)

        for i in range(intl):

            bram_input_ext = [x for x in k.get_bram_inputs() if x.internal == False]
            stream_args = [streamify(c.Value(get_type(arg.c_op), arg.c_op.name + str(i))) for arg in bram_input_ext]
            bram_args = [f"{arg.c_op.name}_buf{i}" for arg in bram_input_ext]
            cs_tok = c.Value("hls::stream<ap_uint<1>>", f"tokenCS{i}") 
            func_body.append(cs_tok)
            func_calls.append(self.call_func(bram_in_func, stream_args+bram_args+[cs_tok]))
            functions.add(bram_in_func)

            sd_tok = c.Value("hls::stream<ap_uint<1>>", f"tokenSD{i}") 
            kernel_start_tok = c.Value("hls::stream<ap_uint<1>>", f"kernel_start{i}") 
            func_body.append(sd_tok)
            start_args = []
            if k.axi_io:
                start_args += [f"tokenAT{i}"]
            start_args += [cs_tok] + [value_rename(x, f"{x.name}{i}") for x in start_toks] + [ sd_tok, kernel_start_tok]
            func_calls.append(self.call_func(start_func, start_args))
            functions.add(start_func)

            de_tok = c.Value("hls::stream<ap_uint<1>>", f"tokenDE{i}") 
            func_body.append(de_tok)
            kernel_done_tok = c.Value("hls::stream<ap_uint<1>>", f"kernel_done{i}") 
            func_calls.append(self.call_func(done_func, [kernel_done_tok, sd_tok, de_tok] + [value_rename(x, f"{x.name}{i}") for x in done_toks]))
            functions.add(done_func)

            bram_output_ext = [x for x in k.get_bram_outputs() if x.internal == False]
            stream_args = [streamify(c.Value(get_type(arg.c_op), arg.c_op.name + str(i))) for arg in bram_output_ext]
            bram_args = [f"{arg.c_op.name}_buf{i}" for arg in bram_output_ext]
            func_calls.append(self.call_func(bram_out_func, stream_args+bram_args+[de_tok]))
            functions.add(bram_out_func)

        if write_func:
            func_args = out_ptrs + write_streams
            func_args.append(self.loop_counter)
            if self.ring_buf > 1:
                func_args.append(self.ring_buf_flag)
            func_calls.append(self.call_func(write_func, func_args))
            functions.add(write_func)

        func_body.extend(func_calls)
        return c.FunctionBody(func_decl, func_body), functions

    def gen_omm(self, netname, network, intl):
        """ Generate the Olympus Memory Manager (OMM) module Vitis HLS code """
        cu_file = c.Collection()
        
        self._omm_includes(cu_file)
    
        cu_file_externC = c.Block()
    
        ### CU Wrapper ###
        # CU parameters
        interface_pragmas = c.Collection()
        arglist = []
        kernel_args = []
        k_interface_pragmas, k_arglist, k_kernel_args = self._omm_intf_pragmas(network, intl)
        interface_pragmas.extend(k_interface_pragmas.contents)
        arglist.extend(k_arglist)
        kernel_args.extend(k_kernel_args)

        ### CU WRAPPER FUNC BODY ###
        cu_body = c.Block()

        # Num times for loop 
        numtimesLoopBody = c.Block()
        # - dataflow pragma
        numtimesLoopBody.append(c.Pragma("HLS dataflow"))
        # - datamover data streams 

        for k in network.kernels:
            f,fs = self._omm_kernel_driver(k, intl)
            if k.total_size:
                cu_file.append(k.total_size)
            cu_file_externC.extend(fs)
            cu_file_externC.append(f)

            driver_args = []
            if k.in_ptrs:
                driver_args.extend([value_rename(x, f"{k.name}{x.name}") for x in k.in_ptrs])
            if k.out_ptrs:
                driver_args.extend([value_rename(x, f"{k.name}{x.name}") for x in k.out_ptrs])

            if k.axi_io:
                driver_args.append(k.base_ptr)
                driver_args.extend(k.axi_io)

                if k.kernel_offsets:
                    driver_args.extend([value_rename(x, f"{x.name}{i}") for x in k.kernel_offsets for i in range(intl)])
                
                base_msbs = value_rename(k.base_msbs, f"{k.base_msbs.name}_{k.name}") 
                driver_args.append(base_msbs)
                arglist.append(base_msbs)
                interface_pragmas.append(c.Pragma(f"HLS INTERFACE mode=ap_none port={base_msbs.name}"))

            if k.stream_io:
                driver_args.extend([value_rename(x, f"{x.name}{i}") for x in k.stream_io for i in range(intl)])

            if k.in_bufs:
                driver_args.extend([value_rename(x, f"{x.name}{i}") for x in k.in_bufs for i in range(intl)])
            if k.out_bufs:
                driver_args.extend([value_rename(x, f"{x.name}{i}") for x in k.out_bufs for i in range(intl)])

            driver_args.extend([c.Value("hls::stream<ap_uint<1>>&", f"{k.name}_kernel_start{i}") for i in range(intl)])
            driver_args.extend([c.Value("hls::stream<ap_uint<1>>&", f"{k.name}_kernel_done{i}") for i in range(intl)])

            for u in k.uses:
                toks = [c.Value("hls::stream<ap_uint<1>>", f"{k.name}_{u}_tok{i}") for i in range(intl)]
                driver_args.extend(toks)

            for u in k.users:
                toks = [c.Value("hls::stream<ap_uint<1>>", f"{u}_{k.name}_tok{i}") for i in range(intl)]
                driver_args.extend(toks)
                numtimesLoopBody.extend(toks)

            driver_args.append(self.loop_counter)
            if self.ring_buf > 1:
                driver_args.append(self.ring_buf_flag)

            # axi in, axi out, base, axi off, axi_kernel offs, str, bufs, starts, done, count, flag
            numtimesLoopBody.append(self.call_func(f, driver_args))


        loopmax = "num_times"
        numtimesLoop = c.For(f"{self.loop_counter.inline()} = 0", f"{self.loop_counter.name} < {loopmax}/{intl}", f"{self.loop_counter.name}++", numtimesLoopBody)
        cu_body.append(interface_pragmas)
        cu_body.append(numtimesLoop)
        cu_body.append(c.Statement("return"))
    
        cu_decl = c.FunctionDeclaration(c.Value("void", self.oCtx.sysname), arglist)
        cu_func = c.FunctionBody(cu_decl, cu_body)
    
        cu_file_externC.append(cu_func)
        cu_file.append(c.LiteralLines('\nextern "C"\n'))
        cu_file.append(cu_file_externC)

        return cu_file
