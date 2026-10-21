CREATE OR REPLACE PACKAGE BODY pkg_order_pricing AS
  -- 10% off any order line of 100 units or more
  FUNCTION line_total(p_qty NUMBER, p_unit_price NUMBER) RETURN NUMBER IS
  BEGIN
    IF p_qty >= 100 THEN
      RETURN ROUND(p_qty * p_unit_price * 0.90, 2);
    END IF;
    RETURN p_qty * p_unit_price;
  END line_total;

  FUNCTION order_total(p_order_id NUMBER) RETURN NUMBER IS
    v_total NUMBER;
  BEGIN
    SELECT SUM(line_total(qty, unit_price)) INTO v_total FROM order_lines WHERE order_id = p_order_id;
    RETURN NVL(v_total, 0);
  END order_total;
END pkg_order_pricing;
/
