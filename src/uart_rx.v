module uart_rx #(
	parameter BAUD_RATE = 9600,		// Скорость передачи (кол-во бит в секунду)
   parameter CLK_FREQ  = 50000000	// Частота тактирующего сигнала (Гц)
) (
	input wire rstn_i,
	input wire clk_i,
	input wire rx_i,
	output reg [7:0]rx_byte_o,
	output reg rbyte_ready_o
	);
    
	//скорость приема и передачи определяется этой константой
	//она рассчитана из исх. тактовой частоты CLK_FREQ и желаемой скорости BAUD_RATE
	//как CLK_FREQ/BAUD_RATE: 50000000/9600 = 5208
	localparam RCONST = 5208;
	
	// Внутренние сигналы
	reg [15:0]cnt;
	reg [3:0]num_bits; //счетчик принятых бит

	//счетчик длительности принимаемого бита
	always @(posedge clk_i or negedge rstn_i)
	begin
		 if (!rstn_i)
			  cnt <= 0;
		 else
		 begin
			  if (cnt == RCONST || num_bits==9)
					cnt <= 0;
			  else
					cnt <= cnt + 1'b1;
		 end
	end

	reg [7:0]shift_reg; //сдвиговый регистр приемника

	always @(posedge clk_i or negedge rstn_i)
	begin
		 if (!rstn_i)
		 begin
			  num_bits <= 0;
			  shift_reg <= 0;
		 end
		 else
		 begin
			  //прием начинается когда rx_i падает в ноль
			  if (num_bits==9 && rx_i==1'b0)
					num_bits <= 0;
			  else
			  if (cnt == RCONST)
					num_bits <= num_bits + 1'b1;
			  
			  //фиксация принятого бита где-то посередине
			  if (cnt == RCONST/2)
					shift_reg <= {rx_i,shift_reg[7:1]};
		 end
	end

	//запоминаем принятый байт по окончании приема
	always @(posedge clk_i or negedge rstn_i)
		 if (!rstn_i)
		 begin
			  rx_byte_o <= 0;
		 end
		 else
		 begin    
		 if (num_bits==9)
			  rx_byte_o <= shift_reg[7:0];
		 end

	reg [1:0]flag;
	always @(posedge clk_i or negedge rstn_i)
		 if (!rstn_i)
			  flag <= 2'b00;
		 else
			  flag <= {flag[0],(num_bits==9)};

	//сигнал готовности принятого байта        
	always @*
		 rbyte_ready_o = (flag==2'b01);
		 
	  
endmodule
