module dsig_gen #(
	parameter DATA_WIDTH = 512,
	parameter ID_WIDTH = 8,
	parameter DSIG_WIDTH = 256,
	parameter PKEY_WIDTH = 256
) (
	input wire clk_i,
	input wire rstn_i,
	input wire [DATA_WIDTH-1:0] message_i,
	input wire get_public_key,
	input wire [ID_WIDTH-1:0] user_id_i,
	output wire [DSIG_WIDTH-1:0] dsig_o,
	output wire [PKEY_WIDTH-1:0] public_key_o
);

endmodule