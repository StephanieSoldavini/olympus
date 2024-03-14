from typing import (
    Annotated,
    TypeAlias
)

from xdsl.dialects.builtin import (
    IntegerType,
    StringAttr,
    IntegerAttr,
#    BoolAttr, #TODO
    Attribute,
)

BoolAttr: TypeAlias = IntegerAttr[Annotated[IntegerType, IntegerType(1)]]

from xdsl.dialects.func import (
    FuncOp
)

from xdsl.traits import (
    HasParent
)

from xdsl.irdl import (
    irdl_attr_definition,
    irdl_op_definition, 
#    optional_attribute_field,
    Generic,
    ParameterDef,
    IRDLOperation,
    Operand,
    attr_def,
    opt_attr_def,
    result_def,
    AttrSizedOperandSegments,
    VarOperand,
    var_operand_def,
    operand_def,
    AnyOf
)
from xdsl.ir import (
    Dialect, 
    TypeAttribute,
    ParametrizedAttribute,
    AttributeCovT,
    OpResult,
)


@irdl_attr_definition
class ChannelType(Generic[AttributeCovT], ParametrizedAttribute, TypeAttribute):
    name = "olympus.channel"
    element_type: ParameterDef[AttributeCovT]

@irdl_attr_definition
class IndexType(Generic[AttributeCovT], ParametrizedAttribute, TypeAttribute):
    name = "olympus.index"
    element_type: ParameterDef[AttributeCovT]

@irdl_op_definition
class ChannelOp(IRDLOperation):
    name = "olympus.channel"

    data: OpResult = result_def(ChannelType)
    # small = bram, stream = stream, complex = axi
    paramType: StringAttr = attr_def(AnyOf([StringAttr("small"), StringAttr("stream"), StringAttr("complex")]))
    depth: IntegerAttr = attr_def(IntegerAttr)
    scratch: BoolAttr = opt_attr_def(BoolAttr)
    persistent: BoolAttr = opt_attr_def(BoolAttr)

@irdl_op_definition
class IndexOp(IRDLOperation):
    name = "olympus.index"
    channel: Operand = operand_def(ChannelType)
    data: OpResult = result_def(IndexType)
    depth: IntegerAttr = attr_def(IntegerAttr)

@irdl_op_definition
class KernelOp(IRDLOperation):
    name = "olympus.kernel"
    traits = frozenset([HasParent(FuncOp)])

    inputs: VarOperand = var_operand_def(AnyOf([ChannelType, IndexType]))
    outputs: VarOperand = var_operand_def(ChannelType)
    inouts: VarOperand = var_operand_def(ChannelType)
    callee: StringAttr = attr_def(StringAttr)
    latency: IntegerAttr = attr_def(IntegerAttr)
    ii: IntegerAttr = attr_def(IntegerAttr)
    bram: IntegerAttr = attr_def(IntegerAttr)
    dsp: IntegerAttr = attr_def(IntegerAttr)
    ff: IntegerAttr = attr_def(IntegerAttr)
    lut: IntegerAttr = attr_def(IntegerAttr)
    uram: IntegerAttr = attr_def(IntegerAttr)
    irdl_options = [AttrSizedOperandSegments()]

Olympus = Dialect(
        [
            ChannelOp,
            KernelOp,
            IndexOp,
        ],
        [
            ChannelType,
            IndexType,
        ]
)

