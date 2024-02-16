module ap_ctrl_to_bambu (
    input  wire ap_clk,
    input  wire ap_rstn,
    input  wire ap_start,
    input  wire ap_done,

    output wire ap_ready,
    output wire ap_idle
);

wire idle_signal;
reg idle_nxt;

assign ap_ready = ap_done;
assign ap_idle = idle_signal;

assign idle_signal = idle_nxt && (~ap_start);

always @(posedge ap_clk) begin
    if (ap_rstn == 1'b0) begin
        idle_nxt = 1'b1;
    end else if (ap_done == 1'b1) begin
        idle_nxt = 1'b1;
    end else begin
        idle_nxt = idle_signal;
    end
end

endmodule
