module dsig_top #(
	 // UART
    parameter DATA_BITS = 24,   		// Количество бит данных, кратное 8
    parameter BAUD_RATE = 9600,		// Скорость передачи (кол-во бит в секунду)
    parameter CLK_FREQ  = 50000000	// Частота тактирующего сигнала (Гц)
) (
	// UART
	(*chip_pin= "23"*)  input wire clk_i,		// Тактовый сигнал
   (*chip_pin= "25"*)  input wire rstn_i,		// Сброс
   (*chip_pin= "115"*) input wire rx_i,     	// Линия приема данных
   (*chip_pin= "114"*) output wire tx_o     	// Линия передачи данных
);
     
	 uart_top #(
        .DATA_BITS	(DATA_BITS	),
		  .BAUD_RATE	(BAUD_RATE	),
		  .CLK_FREQ		(CLK_FREQ	)
    ) uart_top_inst (
        .clk_i  		(clk_i	),
        .rstn_i		(rstn_i	),
        .rx_i  		(rx_i		),
		  .tx_o  		(tx_o		)
    );

endmodule