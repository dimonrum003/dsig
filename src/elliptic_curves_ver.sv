module elliptic_curves_ver #(
	parameter HASH_WIDTH = 256,
	parameter DSIG_WIDTH = 256,
	parameter PKEY_WIDTH = 256
) (
	input wire clk_i,
	input wire rstn_i,
	input wire [HASH_WIDTH-1:0] hash_i,
	input wire [DSIG_WIDTH-1:0] dsig_i,
	input wire [PKEY_WIDTH-1:0] public_key_i,
	output wire dsig_ver_result
);

endmodule