module initiator #( parameter N_KERNELS=1,
    parameter C_AXIS_TDATA_WIDTH = 32
) (
    // Start "signal" stream in
    input  wire                   s_start_axis_aclk,
    input  wire                   s_start_axis_aresetn,
    input  wire [C_AXIS_TDATA_WIDTH-1:0]  s_start_axis_tdata,
    input  wire [(C_AXIS_TDATA_WIDTH/8)-1 : 0] s_start_axis_tstrb,
    input  wire                   s_start_axis_tvalid,
    output wire                   s_start_axis_tready,
    input  wire                   s_start_axis_tlast,

    // Done "signal" stream out
    input  wire                   m_done_axis_aclk,
    input  wire                   m_done_axis_aresetn,
    output wire [C_AXIS_TDATA_WIDTH-1:0]  m_done_axis_tdata,
    output wire [(C_AXIS_TDATA_WIDTH/8)-1 : 0] m_done_axis_tstrb,
    output wire                   m_done_axis_tvalid,
    input  wire                   m_done_axis_tready,
    output wire                   m_done_axis_tlast,

    // Broadcast ap_start to N kernels, collect N ap_done signals
    output wire [N_KERNELS-1:0] ap_start,
    input wire  [N_KERNELS-1:0] ap_done,
    input wire  [N_KERNELS-1:0] ap_idle,
    input wire  [N_KERNELS-1:0] ap_ready
);

reg  start;
wire  done;
wire  idle;
wire  ready;

reg done_tvalid;
reg [N_KERNELS-1:0] done_latch;

always @(posedge s_start_axis_aclk) begin
    if (s_start_axis_aresetn == 1'b0) begin
        start <= 1'b0;
    end else begin
        if ((ready || idle) && s_start_axis_tvalid) begin
            start <= 1'b1;
        end else begin
            start <= 1'b0;
        end
    end
end

genvar i;
generate
    for (i = 0; i < N_KERNELS; i = i + 1) begin
        always @(posedge m_done_axis_aclk) begin
            if (m_done_axis_aresetn == 1'b0) begin
                done_latch[i] <= 1'b0;
            end else begin
                if (done_tvalid) begin
                    done_latch[i] <= 1'b0;
                end else if (ap_done[i]) begin
                    done_latch[i] <= 1'b1; 
                end
            end
        end
    end
endgenerate
    

always @(posedge m_done_axis_aclk) begin
    if (m_done_axis_aresetn == 1'b0) begin
        done_tvalid <= 1'b0;
    end else begin
        //ovalid <= (ovalid && !oready) || !iready || ivalid;
        //done_tvalid <= (done_tvalid && !m_done_axis_tready) || idle; 
        if (done) begin
            done_tvalid <= 1'b1;
        end
        if (done_tvalid && m_done_axis_tready) begin
            done_tvalid <= 1'b0;
        end
    end
end

assign m_done_axis_tvalid = done_tvalid;
assign s_start_axis_tready = idle; //ready;
assign m_done_axis_tdata = 0;
assign m_done_axis_tstrb = 1'b1;
assign m_done_axis_tlast = 1'b1;

assign done = &done_latch;
assign idle = &ap_idle;
assign ready = &ap_ready;

assign ap_start = {N_KERNELS{start}};

endmodule
