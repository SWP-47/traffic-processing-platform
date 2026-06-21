module connection_filter (
    input          e1_rxc_int,
    input          e1_rxdv,
    input [0:7]    e1_rxd

    // output         validity
);

logic [511:0] packet;
logic [511:0] new_packet;
assign new_packet = {packet[503:0], e1_rxd};
logic [7:0] byte_counter;
logic [15:0] etherType;
logic isIPv4;
logic validity;

always_ff @( posedge e1_rxc_int ) begin 
    if (e1_rxdv) begin
        if (byte_counter > 3'd7)
            packet <= new_packet;
        byte_counter <= byte_counter + 1'b1;
        if (byte_counter == 5'd20)
            etherType [15:8] <= e1_rxd;
        if (byte_counter == 5'd21) begin
            etherType [7:0] <= e1_rxd;
            if ({etherType[15:8], e1_rxd} == 16'h0800)
                isIPv4 <= 1'b1;
        end
    end else begin
        // validity <= isIPv4;
        wr_en <= isIPv4;
        isIPv4 <= '0;
        packet <= '0;
        byte_counter <= '0;
        etherType <= '0;
    end
end

endmodule