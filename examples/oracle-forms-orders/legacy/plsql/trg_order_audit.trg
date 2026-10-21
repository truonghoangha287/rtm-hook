CREATE OR REPLACE TRIGGER trg_order_audit
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW
BEGIN
  INSERT INTO order_audit (order_id, action, changed_by, changed_at)
  VALUES (NVL(:NEW.order_id, :OLD.order_id),
          CASE WHEN INSERTING THEN 'I' WHEN UPDATING THEN 'U' ELSE 'D' END,
          USER, SYSTIMESTAMP);
END;
/
