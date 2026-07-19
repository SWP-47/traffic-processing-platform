`timescale 1ns / 1ps

module top
(
    input                           sys_clk_p,                    //system clock positive
    input                           sys_clk_n,                    //system clock negative 
    input                           rst_n,                        //reset ,low active
    //ethernet 1
    output                          e1_reset,                     //phy reset
    output                          e1_mdc,                       //phy emdio clock
    inout                           e1_mdio,                      //phy emdio data
    input	                        e1_rxc,                       //125Mhz ethernet gmii rx clock
    input                           e1_rxdv,                      //GMII recieving data valid
    input                           e1_rxer,                      //GMII recieving data error                    
    input [7:0]                     e1_rxd,                       //GMII recieving data          

    input                           e1_txc,                       //25Mhz ethernet mii tx clock         
    output                          e1_gtxc,                      //125Mhz ethernet gmii tx clock  
    output                          e1_txen,                      //GMII sending data valid    
    output                          e1_txer,                      //GMII sending data error                   
    output[7:0]                     e1_txd,                       //GMII sending data 
    //ethernet 2
    output                          e2_reset,                     //phy reset
    output                          e2_mdc,                       //phy emdio clock
    inout                           e2_mdio,                      //phy emdio data
    input	                        e2_rxc,                       //125Mhz ethernet gmii rx clock
    input                           e2_rxdv,                      //GMII recieving data valid
    input                           e2_rxer,                      //GMII recieving data error                    
    input [7:0]                     e2_rxd,                       //GMII recieving data          

    input                           e2_txc,                       //25Mhz ethernet mii tx clock         
    output                          e2_gtxc,                      //125Mhz ethernet gmii tx clock  
    output                          e2_txen,                      //GMII sending data valid    
    output                          e2_txer,                      //GMII sending data error                   
    output[7:0]                     e2_txd,                       //GMII sending data 
    //ethernet 3
    output                          e3_reset,                     //phy reset
    output                          e3_mdc,                       //phy emdio clock
    inout                           e3_mdio,                      //phy emdio data
    input	                        e3_rxc,                       //125Mhz ethernet gmii rx clock
    input                           e3_rxdv,                      //GMII recieving data valid
    input                           e3_rxer,                      //GMII recieving data error                    
    input [7:0]                     e3_rxd,                       //GMII recieving data          

    input                           e3_txc,                       //25Mhz ethernet mii tx clock         
    output                          e3_gtxc,                      //125Mhz ethernet gmii tx clock  
    output                          e3_txen,                      //GMII sending data valid    
    output                          e3_txer,                      //GMII sending data error                   
    output[7:0]                     e3_txd,                       //GMII sending data 
    //ethernet 4
    output                          e4_reset,                     //phy reset
    output                          e4_mdc,                       //phy emdio clock
    inout                           e4_mdio,                      //phy emdio data
    input	                        e4_rxc,                       //125Mhz ethernet gmii rx clock
    input                           e4_rxdv,                      //GMII recieving data valid
    input                           e4_rxer,                      //GMII recieving data error                    
    input [7:0]                     e4_rxd,                       //GMII recieving data          

    input                           e4_txc,                       //25Mhz ethernet mii tx clock         
    output                          e4_gtxc,                      //125Mhz ethernet gmii tx clock  
    output                          e4_txen,                      //GMII sending data valid    
    output                          e4_txer,                      //GMII sending data error                   
    output[7:0]                     e4_txd,                       //GMII sending data 

    input                           block_but_key,                //Physical button, positive - block
    output                          led,
    output                          debug_led
); 

(* DONT_TOUCH = "yes" *) wire                            sys_clk;     //single end clock


// --------------------------------------------------------------------
// logic block_but;
// logic prev_value;

// assign led = block_but;

// always_ff @( posedge sys_clk ) begin
//     prev_value <= block_but_key;
//     if (!block_but_key && prev_value)
//         block_but <= ~block_but;
// end

// --------------------------------------------------------------------

logic block_but;

but_executor but_executor_inst (
    .rst_n         (  rst_n          ),
    .sys_clk       (  sys_clk        ),
    .block_but_key (  block_but_key  ),
    .block_but     (  block_but      ),
    .led           (  led            )
);

// --------------------------------------------------------------------

IBUFDS sys_clk_ibufgds
(
    .I  ( sys_clk_p ),
    .IB ( sys_clk_n ),
    .O  ( sys_clk   )
);

assign e1_reset = 1'b1;
assign e1_mdc   = 1'bz;
assign e1_mdio  = 1'bz;

assign e2_reset = 1'b1;
assign e2_mdc   = 1'bz;
assign e2_mdio  = 1'bz;

assign e3_reset = 1'b1;
assign e3_mdc   = 1'bz;
assign e3_mdio  = 1'bz;

assign e4_reset = 1'b1;
assign e4_mdc   = 1'bz;
assign e4_mdio  = 1'bz;


logic [31:0] ip_to_block;

block_ip_getter block_ip_getter_inst (
    .rst_n         (  rst_n        ),
    .e_rxer        (  e2_rxer      ),
    .e_rxc         (  e2_rxc       ),
    .e_rxdv        (  e2_rxdv      ),
    .e_rxd         (  e2_rxd       ),

    .ip_to_block_r (  ip_to_block  ),

    .led2 (debug_led)
);


logic in_rxc_read;
logic in_rxdv_read;
logic [7:0] in_rxd_read;


receiver receiver_inst_in_e4 (
    .rst_n     (  rst_n         ),
    .e_rxc     (  e4_rxc        ),
    .e_rxdv    (  e4_rxdv       ),
    .e_rxer    (  e4_rxer       ),
    .e_rxd     (  e4_rxd        ),    

    .rxc_read  (  in_rxc_read   ),
    .rxdv_read (  in_rxdv_read  ),
    .rxd_read  (  in_rxd_read   ) 
);


logic out_rxc_read;
logic out_rxdv_read;
logic [7:0] out_rxd_read;


receiver receiver_inst_out_e1 (
    .rst_n     (  rst_n          ),
    .e_rxc     (  e1_rxc         ),
    .e_rxdv    (  e1_rxdv        ),
    .e_rxer    (  e1_rxer        ),
    .e_rxd     (  e1_rxd         ),     

    .rxc_read  (  out_rxc_read   ),
    .rxdv_read (  out_rxdv_read  ),
    .rxd_read  (  out_rxd_read   ) 
);




logic isBlocked_out;

traffic_monitor traffic_monitor_out_e1 (
    .rst_n       (  rst_n          ),
    .rxc_read    (  out_rxc_read   ),
    .rxdv_read   (  e1_rxdv        ),
    .rxd_read    (  e1_rxd         ), 
    
    .ip_to_block (  ip_to_block    ),
    .block_but   (  block_but      ),
    
    .isBlocked   (  isBlocked_out  )
);


logic isBlocked_in;

traffic_monitor traffic_monitor_in_e1 (
    .rst_n       (  rst_n         ),
    .rxc_read    (  in_rxc_read   ),
    .rxdv_read   (  e4_rxdv       ),
    .rxd_read    (  e4_rxd        ), 
    
    .ip_to_block (  ip_to_block   ),
    .block_but   (  block_but     ),
    
    .isBlocked   (  isBlocked_in  )
);




sender sender_e1 (
    .rst_n        (  rst_n          ),
    .e_txc        (  e1_txc         ),
    .e_gtxc       (  e1_gtxc        ),
    .e_txen       (  e1_txen        ),
    .e_txer       (  e1_txer        ),
    .e_txd        (  e1_txd         ),
    
    .isBlocked    (  isBlocked_in   ),
    
    .gtxc_to_send (  in_rxc_read    ),
    .txen_to_send (  in_rxdv_read   ),
    .txd_to_send  (  in_rxd_read    )
);


sender sender_e2 (
    .rst_n        (  rst_n          ),
    .e_txc        (  e2_txc         ),
    .e_gtxc       (  e2_gtxc        ),
    .e_txen       (  e2_txen        ),
    .e_txer       (  e2_txer        ),
    .e_txd        (  e2_txd         ),
    
    .isBlocked    (  isBlocked_out  ),
    
    .gtxc_to_send (  out_rxc_read   ),
    .txen_to_send (  out_rxdv_read  ),
    .txd_to_send  (  out_rxd_read   )
);


sender sender_e3 (
    .rst_n        (  rst_n          ),
    .e_txc        (  e3_txc         ),
    .e_gtxc       (  e3_gtxc        ),
    .e_txen       (  e3_txen        ),
    .e_txer       (  e3_txer        ),
    .e_txd        (  e3_txd         ),
    
    .isBlocked    (  isBlocked_in   ),
    
    .gtxc_to_send (  in_rxc_read    ),
    .txen_to_send (  in_rxdv_read   ),
    .txd_to_send  (  in_rxd_read    )
);


sender sender_e4 (
    .rst_n        (  rst_n          ),
    .e_txc        (  e4_txc         ),
    .e_gtxc       (  e4_gtxc        ),
    .e_txen       (  e4_txen        ),
    .e_txer       (  e4_txer        ),
    .e_txd        (  e4_txd         ),
    
    .isBlocked    (  isBlocked_out  ),
    
    .gtxc_to_send (  out_rxc_read   ),
    .txen_to_send (  out_rxdv_read  ),
    .txd_to_send  (  out_rxd_read   )
);


ila_0 ila_0_inst (
    .clk (e2_rxc),
    .probe0(e2_rxd),
    .probe1(ip_to_block),
    .probe2(e2_rxdv)
);
// -------------------------------------------------------------------------
//  wire [7:0]    probe_out0;
//  wire [7:0]    probe_out1;
//  wire [7:0]    probe_out2;
//  wire [7:0]    probe_out3;
  
//vio_1 VIO_INST
//(
//  .clk          (sys_clk         ),
//  .probe_in0    (e1_rxd   ),
//  .probe_in1    (e2_rxd   ),
//  .probe_in2    (e1_txd   ),
//  .probe_in3    (e2_txd   ),
//  .probe_out0    (probe_out0   ),
//  .probe_out1    (probe_out1   ),
//  .probe_out2    (probe_out2   ),
//  .probe_out3    (probe_out3   )
//);

    endmodule