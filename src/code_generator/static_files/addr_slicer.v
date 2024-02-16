module addr_slicer #( parameter FULL_ADDR_WIDTH = 64,
    parameter ACCESS_ADDR_WIDTH = 29
) (
    input  wire [FULL_ADDR_WIDTH-ACCESS_ADDR_WIDTH-1:0] i_base_msbs,
    input  wire [FULL_ADDR_WIDTH-1:0] i_kernel_raddr,
    input  wire [FULL_ADDR_WIDTH-1:0] i_kernel_waddr,
    output wire [FULL_ADDR_WIDTH-1:0] o_gmem_raddr,
    output wire [FULL_ADDR_WIDTH-1:0] o_gmem_waddr
);

assign o_gmem_raddr = {i_base_msbs, i_kernel_raddr[ACCESS_ADDR_WIDTH-1:0]};
assign o_gmem_waddr = {i_base_msbs, i_kernel_waddr[ACCESS_ADDR_WIDTH-1:0]};

endmodule
