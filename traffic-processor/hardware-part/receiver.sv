module receiver (
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

assign rxdv_read = e_rxdv;
assign rxd_read = e_rxd;


endmodule