module traffic_monitor (
    input                           rxc_read,
    input                           rxdv_read,
    input [7:0]                     rxd_read,

    input                           block_but,
    
    output                          isBlocked
);

assign isBlocked = '0;

endmodule