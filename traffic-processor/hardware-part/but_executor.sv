module but_executor (
    input                           rst_n,
    input                           sys_clk,

    input                           block_but_key,
    output reg                      block_but,
    output                          led
);


logic prev_value;

assign led = block_but;

always_ff @( posedge sys_clk ) begin
    if (rst_n) begin
        prev_value <= block_but_key;
        if (!block_but_key && prev_value)
            block_but <= ~block_but;
    end else begin
        prev_value <= '0;
        block_but <= '0;
    end
end



endmodule