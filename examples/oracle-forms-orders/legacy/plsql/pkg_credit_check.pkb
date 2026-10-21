CREATE OR REPLACE PACKAGE BODY pkg_credit_check AS
  PROCEDURE assert_within_limit(p_customer_id NUMBER, p_new_amount NUMBER) IS
    v_limit NUMBER; v_open NUMBER;
  BEGIN
    SELECT credit_limit INTO v_limit FROM customers WHERE customer_id = p_customer_id;
    SELECT NVL(SUM(total), 0) INTO v_open FROM orders WHERE customer_id = p_customer_id AND status = 'OPEN';
    IF v_open + p_new_amount > v_limit THEN
      RAISE_APPLICATION_ERROR(-20010, 'Credit limit exceeded');
    END IF;
  END assert_within_limit;
END pkg_credit_check;
/
