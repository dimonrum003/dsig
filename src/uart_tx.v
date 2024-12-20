module uart_tx #(
	parameter BAUD_RATE = 9600,		// Скорость передачи (кол-во бит в секунду)
   parameter CLK_FREQ  = 50000000	// Частота тактирующего сигнала (Гц)
) (
	input wire rstn_i,
	input wire clk_i,    
	input wire [7:0]sbyte_i,
	input wire send_i,
	output reg tx_o,
	output reg busy_o 
	);

	//скорость приема и передачи определяется этой константой
	//она рассчитана из исх. тактовой частоты CLK_FREQ и желаемой скорости BAUD_RATE
	//как CLK_FREQ/BAUD_RATE: 50000000/9600 = 5208
	localparam RCONST = 5208;
    
	// Внутренние сигналы
	reg [8:0]send_reg;
	reg [3:0]send_num;
	reg [15:0]send_cnt;
	wire send_time; 
	
	assign send_time = (send_cnt == RCONST);

	always @(posedge clk_i or negedge rstn_i)
	begin
		 if (!rstn_i)
		 begin
			  send_reg <= 0;
			  send_num <= 0;
			  send_cnt <= 0;
		 end
		 else
		 begin
			  //передача начинается по сигналу send_i
			  if (send_i)
					send_cnt <= 0;
			  else
					if (send_time)
						 send_cnt <= 0;
					else
						 send_cnt <= send_cnt + 1'b1;
			  
			  if (send_i)
			  begin
					//загружаем передаваемый байт в сдвиговый регистр по сигналу send_i
					send_reg <= {sbyte_i,1'b0};
					send_num <= 0;
			  end
			  else 
			  if (send_time && send_num!=10)
			  begin
					//выдвигаем передаваемый байт
					send_reg <= {1'b1,send_reg[8:1]};
					send_num <= send_num + 1'b1;
			  end
		 end
	end

	always @*
	begin
		 busy_o = (send_num!=10);
		 tx_o = send_reg[0];
	end
	
endmodule
