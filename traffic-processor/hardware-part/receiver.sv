module receiver (
    input                           rst_n,
    input	                        e_rxc,
    input                           e_rxdv,
    input                           e_rxer,
    input [7:0]                     e_rxd,
        
    output                          rxc_read,
    output                          rxdv_read,
    output [7:0]                    rxd_read 
);


BUFG e1_rx_clk_buf
(
    .I (e_rxc),
    .O (rxc_read)
);


// assign rxd_read = e_rxd;



// ---------------------------------------------------------------
// logic [8:0] byte_counter;
// logic [8:0] new_byte_counter;
// assign new_byte_counter = byte_counter + 1'b1;

// always_ff @( posedge rxc_read ) begin 
//     if (e_rxdv) begin
//         byte_counter <= new_byte_counter;
//     end else begin
//         byte_counter <= 8'b0;
//     end
// end

logic [43:0] txen_bus;
logic [351:0] txd_bus; 
logic [43:0] txen_bus_r;
logic [351:0] txd_bus_r; 

logic [7:0] next_byte_txd_bus;
always_comb begin
    if (e_rxdv)
        next_byte_txd_bus = e_rxd;
    else
        next_byte_txd_bus = 8'b0;
end

assign txd_bus = {txd_bus_r[343:0], next_byte_txd_bus};
assign txen_bus = {txen_bus_r[42:0], e_rxdv};


always_ff @(  posedge rxc_read  ) begin
    if (!rst_n) begin
        txd_bus_r <= 352'b0;
        txen_bus_r <= 44'b0;
    end else begin
        txd_bus_r <= txd_bus;
        txen_bus_r <= txen_bus;
    end
end

assign rxdv_read = txen_bus_r[43];
assign rxd_read = txd_bus_r[351:344];
// ---------------------------------------------------------------

endmodule