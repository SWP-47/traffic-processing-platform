module traffic_monitor (
    input                           rst_n,

    input                           rxc_read,
    input                           rxdv_read,
    input [7:0]                     rxd_read,

    input                           block_but,
    input [31:0]                    ip_to_block,
    
    output                          isBlocked
);

// assign isBlocked = 1'b1;
// localparam [31:0] ip_to_block = 32'hC0A84D8F;

logic [11:0] byte_counter;

logic [15:0] Ethertype;
logic [15:0] Ethertype_r;

logic [31:0] dst_ip;
logic [31:0] src_ip;


assign isBlocked = (dst_ip == ip_to_block || src_ip == ip_to_block) && byte_counter > 41;



always_ff @( posedge rxc_read ) begin
    if (rst_n) begin
        if (rxdv_read && block_but) begin
            if (byte_counter >= 34 && byte_counter < 38) 
                src_ip <= {src_ip[23:0], rxd_read};
            if (byte_counter >= 38 && byte_counter < 42) 
                dst_ip <= {dst_ip[23:0], rxd_read};
        end else begin
            src_ip <= 32'b0;
            dst_ip <= 32'b0;
        end
    end else begin
        src_ip <= 32'b0;
        dst_ip <= 32'b0;
    end
end




always_ff @(  posedge rxc_read  ) begin
    if (rst_n) begin
        if (rxdv_read && block_but) begin
            if (byte_counter == 12'd20)
                Ethertype_r[15:8] <= rxd_read;
            else if (byte_counter == 12'd21)
                Ethertype_r[7:0] <= rxd_read;
            else if (byte_counter < 12'd20)
                Ethertype_r <= 16'b0;
        end else
            Ethertype_r <= 16'b0;
    end else 
        Ethertype_r <= 16'b0;
end




always_ff @(  posedge rxc_read  ) begin 
    if (rst_n) begin
        if (rxdv_read && block_but)
            byte_counter <= byte_counter + 1'b1;
        else
            byte_counter <= 12'b0;
    end else 
        byte_counter <= 12'b0;
end


endmodule