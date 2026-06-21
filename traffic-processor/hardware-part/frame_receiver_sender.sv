`timescale 1ns / 1ps

module frame_receiver_sender
(
    input                           sys_clk_p,                    //system clock positive
    input                           sys_clk_n,                    //system clock negative 
    input                           rst_n,                        //reset ,low active
    output[1:0]                     led,                          //display network rate status
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
    output[7:0]                     e4_txd                        //GMII sending data 

); 

    (* DONT_TOUCH = "yes" *) wire                            sys_clk;                      //single end clock


    IBUFDS sys_clk_ibufgds
    (
        .I  ( sys_clk_p ),
        .IB ( sys_clk_n ),
        .O  ( sys_clk   )
    );
    


    wire e1_rxc_int;
    wire e1_gtxc_int;

    BUFG e1_rx_clk_buf
    (
        .I (e1_rxc),
        .O (e1_rxc_int)
    );

    BUFG e1_tx_clk_buf
    (
        .I (e1_gtxc_int),
        .O (e1_gtxc)
    );


    
    wire e4_rxc_int;
    wire e4_gtxc_int;

    BUFG e4_rx_clk_buf
    (
        .I (e4_rxc),
        .O (e4_rxc_int)
    );

    BUFG e4_tx_clk_buf
    (
        .I (e4_gtxc_int),
        .O (e4_gtxc)
    );


    
    wire e2_gtxc_int;

    BUFG e2_tx_clk_buf
    (
        .I (e2_gtxc_int),
        .O (e2_gtxc)
    );
    

    
    wire e3_gtxc_int;

    BUFG e3_tx_clk_buf
    (
        .I (e3_gtxc_int),
        .O (e3_gtxc)
    );


    // eth_rx_ila_0 ila_e0_rx
    // (
    //     .clk    ( e1_rxc_int ),
    //     .probe0 ( e1_rxdv    ),
    //     .probe1 ( e1_rxer    ),
    //     .probe2 ( e1_rxd     )
    // );

    
    assign e1_reset    = 1'b1;
    assign e1_mdc      = 1'bz;
    assign e1_mdio     = 1'bz;
    assign e1_gtxc_int = e4_rxc_int;
    assign e1_txen     = e4_rxdv;
    assign e1_txer     = e4_rxer;
    assign e1_txd      = e4_rxd;

    assign e2_reset    = 1'b1;
    assign e2_mdc      = 1'bz;
    assign e2_mdio     = 1'bz;
    assign e2_gtxc_int = e1_rxc_int;
    assign e2_txen     = e1_rxdv;
    assign e2_txer     = e1_rxer;
    assign e2_txd      = e1_rxd;


    assign e3_reset    = 1'b1;
    assign e3_mdc      = 1'bz;
    assign e3_mdio     = 1'bz;
    assign e3_gtxc_int = e4_rxc_int;
    assign e3_txen     = e4_rxdv;
    assign e3_txer     = e4_rxer;
    assign e3_txd      = e4_rxd;


    assign e4_reset    = 1'b1;
    assign e4_mdc      = 1'bz;
    assign e4_mdio     = 1'bz;
    assign e4_gtxc_int = e1_rxc_int;
    assign e4_txen     = e1_rxdv;
    assign e4_txer     = e1_rxer;
    assign e4_txd      = e1_rxd;


    // connection_filter connection_filter_inst (
    //     .e1_rxc_int (  e1_rxc_int  ),
    //     .e1_rxdv    (  e1_rxdv     ),
    //     .e1_rxd     (  e1_rxd      )
    // );



// /*************************************************************************
// ehternet 1 test
// **************************************************************************/
// ethernet_test u1
// (
// .sys_clk                        (sys_clk                ),
// .rst_n                          (rst_n                  ),
// .e_reset                        (e1_reset               ), 
// .e_mdc                          (e1_mdc                 ),        
// .e_mdio                         (e1_mdio                ), 
// .e_rxc                          (e1_rxc                 ), 
// .e_rxdv                         (e1_rxdv                ), 
// .e_rxer                         (e1_rxer                ), 
// .e_rxd                          (e1_rxd                 ), 
// .led                            (led_r1                 ),
// .e_txc                          (e1_txc                 ), 
// .e_gtxc                         (e1_gtxc                ), 
// .e_txen                         (e1_txen                ), 
// .e_txer                         (e1_txer                ),
// .e_txd                          (e1_txd                 )        
// );
// /*************************************************************************
// ehternet 2 test
// **************************************************************************/
// ethernet_test u2
// (
// .sys_clk                        (sys_clk                ),
// .rst_n                          (rst_n                  ),
// .e_reset                        (e2_reset               ), 
// .e_mdc                          (e2_mdc                 ),        
// .e_mdio                         (e2_mdio                ), 
// .e_rxc                          (e2_rxc                 ), 
// .e_rxdv                         (e2_rxdv                ), 
// .e_rxer                         (e2_rxer                ), 
// .e_rxd                          (e2_rxd                 ), 
// .led                            (led_r2                 ),
// .e_txc                          (e2_txc                 ), 
// .e_gtxc                         (e2_gtxc                ), 
// .e_txen                         (e2_txen                ), 
// .e_txer                         (e2_txer                ),
// .e_txd                          (e2_txd                 )        
// );
// /*************************************************************************
// ehternet 3 test
// **************************************************************************/
// ethernet_test u3
// (
// .sys_clk                        (sys_clk                ),
// .rst_n                          (rst_n                  ),
// .e_reset                        (e3_reset               ), 
// .e_mdc                          (e3_mdc                 ),        
// .e_mdio                         (e3_mdio                ), 
// .e_rxc                          (e3_rxc                 ), 
// .e_rxdv                         (e3_rxdv                ), 
// .e_rxer                         (e3_rxer                ), 
// .e_rxd                          (e3_rxd                 ), 
// .led                            (led_r3                 ),
// .e_txc                          (e3_txc                 ), 
// .e_gtxc                         (e3_gtxc                ), 
// .e_txen                         (e3_txen                ), 
// .e_txer                         (e3_txer                ),
// .e_txd                          (e3_txd                 )        
// );
// /*************************************************************************
// ehternet 4 test
// **************************************************************************/
// ethernet_test u4
// (
// .sys_clk                        (sys_clk                ),
// .rst_n                          (rst_n                  ),
// .e_reset                        (e4_reset               ), 
// .e_mdc                          (e4_mdc                 ),        
// .e_mdio                         (e4_mdio                ), 
// .e_rxc                          (e4_rxc                 ), 
// .e_rxdv                         (e4_rxdv                ), 
// .e_rxer                         (e4_rxer                ), 
// .e_rxd                          (e4_rxd                 ), 
// .led                            (led_r4                 ),
// .e_txc                          (e4_txc                 ), 
// .e_gtxc                         (e4_gtxc                ), 
// .e_txen                         (e4_txen                ), 
// .e_txer                         (e4_txer                ),
// .e_txd                          (e4_txd                 )        
// );

endmodule
