"builtin.module"() ({
    "func.func"() ({
        ^bb0():
        %S = "olympus.channel"() {paramType = "small", depth = 121 } : () -> (!olympus.channel<i64>)
        %D = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)
        %u = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)
        %v = "olympus.channel"() {paramType = "small", depth = 1331} : () -> (!olympus.channel<i64>)

        "olympus.kernel"(%S, %D, %u, %v) {callee = "helmholtz", evp.path = "./input/helmholtz.cpp",
            latency = 13876, ii = 13876, bram = 2, dsp = 134, ff = 36891, lut = 22977, uram = 9,
            operandSegmentSizes = array<i32: 3, 1, 0>} : 
            (!olympus.channel<i64>, !olympus.channel<i64>, !olympus.channel<i64>, !olympus.channel<i64>) -> ()
        "func.return"() : () -> ()
    }) {function_type = () -> () , sym_name = "helm_top"} : () -> ()
}) : () -> ()

