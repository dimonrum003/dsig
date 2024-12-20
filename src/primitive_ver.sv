module primitive_ver #(
	parameter DATA_WIDTH = 512,
	parameter DSIG_WIDTH = 256,
	parameter PKEY_WIDTH = 256
) (
	input wire clk_i,
	input wire rstn_i,
	input wire [DATA_WIDTH-1:0] message_i,
	input wire [DSIG_WIDTH-1:0] dsig_i,
	input wire [PKEY_WIDTH-1:0] public_key_i,
	output wire dsig_ver_result
);

endmodule