module block_ip_getter (
    input                           rst_n,
    input                           e_rxer,
    input                           e_rxc,
    input                           e_rxdv,
    input [7:0]                     e_rxd,
    
    output reg [31:0]               ip_to_block_r,

    output reg                         led2               
);

logic rxc_read;

BUFG e_rx_clk_buf
(
    .I (e_rxc),
    .O (rxc_read)
);

// localparam [31:0] ip_to_block = 32'hC0A84D8E;

logic [11:0] byte_counter;

logic [15:0] Ethertype_r;

logic [31:0] new_ip_to_block;
logic [31:0] spec_frame_marker;

// logic [31:0] ip_to_block;

// always_comb begin
//     if (new_ip_to_block != 32'b0)
//         ip_to_block = new_ip_to_block;
//     else
        
// end
//-------------------------------------------------------------------------------
logic [31:0] next_r;

assign led2 = 1'b1;
// always_ff @(posedge rxc_read) begin 
//     if (!e_rxdv)
//         led2 <= 1'b1;
//    else
//        if (next_r == 32'hDEADC0DE) 
//            led2 <= 1'b0;
// end

always_ff @(posedge rxc_read) begin
    if (!rst_n)
        next_r <= 32'b0;
    else
        next_r = {next_r[23:0], e_rxd}; 
end
//-------------------------------------------------------------------------------


always_ff @( posedge rxc_read ) begin 
    if (~rst_n)
        ip_to_block_r <= 32'b0;
    else begin
        if (byte_counter == 50 && spec_frame_marker == 32'hDEADC0DE)
            ip_to_block_r <= new_ip_to_block;
    end
end


always_ff @( posedge rxc_read ) begin
    if (e_rxdv) begin
        if (byte_counter >= 42 && byte_counter < 46) 
            spec_frame_marker <= {spec_frame_marker[23:0], e_rxd};
        if (byte_counter >= 46 && byte_counter < 50) 
            new_ip_to_block <= {new_ip_to_block[23:0], e_rxd};
    end else begin
        spec_frame_marker <= 32'b0;
        new_ip_to_block <= 32'b0;
    end
end




always_ff @(  posedge rxc_read  ) begin
    if (e_rxdv) begin
        if (byte_counter == 12'd20)
            Ethertype_r[15:8] <= e_rxd;
        else if (byte_counter == 21)
            Ethertype_r[7:0] <= e_rxd;
        else if (byte_counter < 20)
            Ethertype_r <= 16'b0;
    end else
        Ethertype_r <= 16'b0;
end




always_ff @(  posedge rxc_read  ) begin 
    if (e_rxdv)
        byte_counter <= byte_counter + 1'b1;
    else
        byte_counter <= 11'b0;
end
endmodule
