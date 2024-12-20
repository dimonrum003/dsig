module ecc_point_mult #(parameter WIDTH = 256) (
    input [WIDTH-1:0] k,             // Скаляр (число)
    input [WIDTH-1:0] Px,            // Координата X точки P
    input [WIDTH-1:0] Py,            // Координата Y точки P
    input [WIDTH-1:0] a,             // Коэффициент 'a' эллиптической кривой
    input [WIDTH-1:0] p,             // Модуль эллиптической кривой
    output reg [WIDTH-1:0] Rx,       // Координата X результирующей точки R
    output reg [WIDTH-1:0] Ry        // Координата Y результирующей точки R
);
    // Временные регистры для хранения промежуточных значений
    reg [WIDTH-1:0] Qx, Qy;  // Текущая точка Q
    reg [WIDTH-1:0] Tx, Ty;  // Промежуточная точка для добавления
    integer i;

    // Вспомогательная функция для сложения точек на эллиптической кривой
    function [2*WIDTH-1:0] add_points(
        input [WIDTH-1:0] X1, Y1, X2, Y2, a, p
    );
        reg [WIDTH-1:0] lambda, num, denom, denom_inv;
		  reg signed [WIDTH-1:0] x3, y3;
        begin
            if ((X1 == X2) && (Y1 == Y2)) begin
                // Удвоение точки
                num = (3 * X1 * X1 + a) % p;
                denom = (2 * Y1) % p;
            end else begin
                // Сложение разных точек
                num = (Y2 - Y1) % p;
                denom = (X2 - X1) % p;
            end

            // Вычисляем обратный элемент для знаменателя
            denom_inv = mod_inverse(denom, p);

            // Вычисляем наклон (λ)
            lambda = (num * denom_inv) % p;

            // Вычисляем координаты новой точки
            x3 = (lambda * lambda - X1 - X2) % p;
            y3 = (lambda * (X1 - x3) - Y1) % p;

            // Убираем отрицательные значения
            if (x3 < 0) x3 = x3 + p;
            if (y3 < 0) y3 = y3 + p;

            // Возвращаем координаты
            add_points = {x3, y3};
        end
    endfunction

    // Вспомогательная функция для нахождения обратного числа по модулю
    function [WIDTH-1:0] mod_inverse(
        input [WIDTH-1:0] a,
        input [WIDTH-1:0] p
    );
        reg [WIDTH-1:0] t, new_t, r, new_r, temp, quotient;
        begin
            t = 0; new_t = 1;
            r = p; new_r = a;

            while (new_r != 0) begin
                quotient = r / new_r;

                temp = new_r;
                new_r = r - quotient * new_r;
                r = temp;

                temp = new_t;
                new_t = t - quotient * new_t;
                t = temp;
            end

            if (t < 0) t = t + p;
            mod_inverse = t;
        end
    endfunction

    always @(*) begin
        // Инициализация начальной точки
        Qx = 0;
        Qy = 0;
        Rx = 0;
        Ry = 0;

        Tx = Px;
        Ty = Py;

        // Алгоритм двойного и добавления
        for (i = 0; i < WIDTH; i = i + 1) begin
            if (k[i] == 1) begin
                {Rx, Ry} = add_points(Rx, Ry, Tx, Ty, a, p);
            end
            {Tx, Ty} = add_points(Tx, Ty, Tx, Ty, a, p);
        end
    end
endmodule
