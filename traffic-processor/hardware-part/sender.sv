module sender (
    input                           rst_n,
    input                           e_txc,
    output                          e_gtxc,
    output reg                      e_txen,
    output                          e_txer,
    output reg [7:0]                e_txd,

    input                           isBlocked,
    
    input                           gtxc_to_send,
    input                           txen_to_send,
    input[7:0]                      txd_to_send
);

logic isBlocked_r;
always_ff @( posedge gtxc_to_send ) begin
    if (rst_n) begin
        if (isBlocked && txen_to_send)
            isBlocked_r <= 1'b1;
        else if (!txen_to_send)
            isBlocked_r <= '0;
    end else begin
        isBlocked_r <= '0;
    end
end

BUFG e1_tx_clk_buf
(
    .I (gtxc_to_send),
    .O (e_gtxc)
);

assign e_txer = '0;

always_ff @( posedge e_gtxc ) begin
    if (!isBlocked_r) begin
        e_txen <= txen_to_send;
        e_txd <= txd_to_send;
    end
    else begin
        e_txen <= '0;
        e_txd <= 8'b0;
    end
end



endmodule