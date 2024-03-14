# olympus
design methOds for simpLifYing the creation of doMain-sPecific memory architectUreS

Necessary dependencies:

`python3.10`

Python dependencies:

`pip3 install cgen`
`pip3 install xdsl`

Tested with Xilinx tools version 2021.1, change path to tools in `targetplatform/alveo/platform_cfg.Makefile`

Olympus requires the system-level specification of the application task
to be synthesized in hardware (to understand how to connect the kernels)
and the platform description. The application description is described
in MLIR (as produced by the compilation phase), while the platform
description is in JSON format.

## Application Description

An example of an application file for the Helmholtz test case is the
following:

``` {.mlir language="mlir" numbers="none" breaklines="true" basicstyle="\\small\\ttfamily" autogobble=""}
"builtin.module"() ({
  "func.func"() ({
    ^bb0():
    %S = "olympus.channel"() {paramType = "small", depth = 121 } : () -> (!olympus.channel<i64>)
    %D = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)
    %u = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)
    %r = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)

    "olympus.kernel"(%S, %D, %u, %r) {callee = "helmholtz", evp.path = "./input/helmholtz.cpp",
      latency = 13876, ii = 13876, bram = 2, dsp = 134, ff = 36891, lut = 22977, uram = 9,
      operandSegmentSizes = array<i32: 3, 1, 0>} : 
      (!olympus.channel<i64>, !olympus.channel<i64>, !olympus.channel<i64>, !olympus.channel<i64>) -> ()
  }) {function_type = () -> () , sym_name = "helm_top"} : () -> ()
}) : () -> ()
```

An application is a collection of kernels (`olympus.kernel`), each of
them characterized by an identifier (`callee`). Each kernel has a
reference of the source file for HLS (`evp.path`). After HLS, the same
description is updated with information about performance and resource
usage. The kernel description also contains information about
connectivity that is used to properly determine the interfaces to be
created. More information can be found in . Olympus automatically
extracts information on the input/output data structures necessary for
the execution and optimizes the memory architecture accordingly.

More details on this dialect are below.

## Platform Description

An example of a platform description file is the following:

    {
      "platform": {
        "name" : "everest_cluster",
        "nodes" : [
          {
            "name" : "node1",
            "type" : ["xilinx_u280_xdma_201920_3"]
            "num_boards" : [2]
          },
          {
            "name" : "node2",
            "type" : ["xilinx_u55c_gen3x16_xdma_3_202210_1"]
          }
        ]
      }
    }

It specifies a heterogeneous cluster with two nodes: the first has an
Alveo u280, i.e., a PCIe-attached FPGA, while the second is a
network-attached cloudFPGA. Indeed, the attribute `type` specifies the
node type. Currently, the following identifiers are supported:
`xilinx_u280_xdma_201920_3` (for Alveo u280 nodes) and
`xilinx_u55c_gen3x16_xdma_3_202210_1` (for Alveo u55 nodes). Supporting new target platforms
requires writing an additional file (under the folder `targetplatform`)
that contains the relevant characteristics (e.g., number of memory
channels, bandwidth, etc.). It is also possible to specify how many
boards are attached to the node. Since EVEREST platforms support nodes
where it is possible to attach different FPGAs, both attributes `type`
and `num_boards` are lists, where the list `num_boards` follows a
positional correspondence with respect to the list `type`.

## Execution Command

Olympus can be executed as follows

    olympus --platform ./platform.json --application ./application.mlir --output ./out

where `platform.json` is the platform description file and
`application.mlir` is the system-level description of the accelerator to
be synthesized. In the output folder, Olympus generates a set of
sub-folders, one for each node, that contain the projects to be
synthesized with the backend tools.


## MLIR Input Format

**Kernel operator**

*Return:* *void* (Any outputs are the last parameters)

*Attributes:*

`callee` : The name of the kernel implementation (C function, Verilog
module, etc)

`latency, ii` : Timing estimates (latency, initiation interval) from
kernel HLS/synthesis

`ff, lut, bram, uram, dsp` : Resource estimates from kernel
HLS/synthesis

`operand_segment_size` : Defines which parameters are inputs and
outputs. (In this example, the '2' in index 0 means the first two
parameters are inputs. The '1' in index 1 means the next 1 parameter is
the output.)

`path` : Where to find the kernel implementation file.

*Parameters:* The inputs and outputs as determined by
`operand_segment_size`. Either scalar data of primitive types or
olympus.channel types. In the same order as in the kernel
implementation.

**Channel operator**

    %2 = "olympus.channel"() {
        paramType = "stream",
        depth = 20
    } : () -> (
        !olympus.channel<i32>
    )

*Return:* *The channel, to be used as input/output operands in kernel
operators.*

*Attributes:*

`paramType` : describes the properties of the data in one of three ways:

-   "`stream`": Must be produced and consumed in the same order and
    consist of small, statically sized elements.

-   "`small`": Can be random access, but in total the data needed for a
    single kernel iteration should be at most on the scale of 100s of kB
    and be organized of simple structures without nesting or
    indirection.

-   "`complex`": Can be anything: huge, random access, have indirection,
    and/or be constructed of nested structures.

`depth` : Describes how large the data is in total. If
`paramType==stream`, `depth` is the maximum necessary channel depth. If
`paramType==small`, `depth` is the number of elements. If
`paramType==complex`, `depth` is the number of bytes.

**Channel type**

    !olympus.channel<i32>

*Type parameter:* A signless integer of arbitrary bitwidth. The
interpretation of the data is not important, only the width. Therefore a
32-bit float, a fixed-point value with 10 integer bits and 22 fraction
bits, and a 32-bit integer should all be represented as '`i32`'.


