module uart_top #(
	parameter DATA_BITS = 24,   		// Количество бит данных, кратное 8
	parameter BAUD_RATE = 9600,		// Скорость передачи (кол-во бит в секунду)
	parameter CLK_FREQ  = 50000000	// Частота тактирующего сигнала (Гц)
) (
	input wire rstn_i,
	input wire clk_i,
	input wire rx_i,
	output wire tx_o
	);

	// Внутренние сигналы
	reg [DATA_BITS-1:0] data_reg; 		// Регистр входящих данных
	reg [DATA_BITS-1:0] sent_data_reg; 	// Регистр данных для отправки
	reg [7:0] sbyte_i;						// Байт для отправки
	reg [1:0] byte_count;     				// Счетчик принятых байтов (до 3)
	reg [2:0] sent_byte_count;   			// Счетчик отправленных байтов (до 3)
	reg data_ready;           				// Флаг готовности данных для передачи
	reg tx_start_i;             			// Сигнал начала передачи
	reg rx_clk_en;								// Сигнал для управления тактовым сигналом для rx
	reg data_almost_ready;					// Вспомогательный сигнал для сдвига на такт
	reg data_almost_finally_ready;		// Вспомогательный сигнал для сдвига на еще один такт
	wire [7:0] rx_byte_o; 					// Принятый байт
	wire rbyte_ready_o; 						// Сигнал о приеме байта
	wire tx_busy_o;             			// Сигнал занятости передатчика
	wire rx_clk_i;								// Тактовый сигнал для rx

	assign rx_clk_i = rx_clk_en ? clk_i : 1'b0;

	// Подключение модуля приемника
	uart_rx #(
	  .BAUD_RATE		(BAUD_RATE		),
	  .CLK_FREQ			(CLK_FREQ		)
	) uart_rx_inst (
	  .rstn_i			(rstn_i			),
	  .clk_i				(rx_clk_i		),
	  .rx_i				(rx_i				),
	  .rx_byte_o		(rx_byte_o		),
	  .rbyte_ready_o	(rbyte_ready_o	)
	);

	// Подключение модуля передатчика
	uart_tx #(
	  .BAUD_RATE	(BAUD_RATE	),
	  .CLK_FREQ		(CLK_FREQ	)
	) uart_tx_inst (
	  .rstn_i		(rstn_i		),
	  .clk_i			(clk_i		),
	  .sbyte_i		(sbyte_i		),
	  .send_i		(tx_start_i	),
	  .tx_o			(tx_o			),
	  .busy_o		(tx_busy_o	)
	);


	// Логика приема и отправки данных
	always @(posedge clk_i or negedge rstn_i)
	begin
	  if (!rstn_i)
	  begin
			data_reg <= 0;
			sent_data_reg <= 0;
			byte_count <= 0;
			data_ready <= 0;
			tx_start_i <= 0;
			rx_clk_en <= 1;
			sent_byte_count <= 0;
			sbyte_i <= 0;
			data_almost_ready <= 0;
			data_almost_finally_ready <= 0;
	  end else if (rbyte_ready_o && !data_almost_ready)
	  begin
			// Прием данных: по мере готовности байтов, добавляем их в data_reg
			data_reg <= {data_reg[15:0], rx_byte_o};  // Сдвигаем и добавляем байт
			byte_count <= byte_count + 1'b1;

			// Когда получено 3 байта, останавливаем прием и устанавливаем флаг готовности
			if (byte_count == 3)
			begin
				 data_almost_ready <= 1;
				 rx_clk_en <= 0;	 
			end
	  end else if (data_almost_ready && !data_almost_finally_ready)
	  begin
			data_almost_finally_ready <= 1;
			sent_data_reg <= data_reg;
	  end else if (data_almost_finally_ready && !data_ready)
	  begin
			data_ready <= 1;
			tx_start_i <= 1;
	  end else if (data_ready && !tx_busy_o && sent_byte_count < 3)
	  begin
			// Запуск передачи данных по tx
			tx_start_i <= 1;
			data_ready <= 0;  // Сбрасываем флаг готовности после начала передачи
			//byte_count <= 0;  // Сброс счетчика байтов для следующего приема
			sent_byte_count <= sent_byte_count + 1'b1;
			sbyte_i <= sent_data_reg[23:16];
			sent_data_reg <= {sent_data_reg[15:0], {8{1'b0}}};
	  end else
	  begin
			tx_start_i <= 0;
	  end
	end

endmodule
