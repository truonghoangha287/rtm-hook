CREATE OR REPLACE PACKAGE BODY pkg_renewal AS
  -- Nightly DBMS_SCHEDULER job RENEWAL_JOB
  PROCEDURE create_renewal_quotes IS
  BEGIN
    FOR p IN (SELECT p.policy_no, h.dob, h.ncd_years, v.vehicle_value,
                     (SELECT COUNT(*) FROM claims c WHERE c.policy_no = p.policy_no) AS claim_count
                FROM policies p JOIN policy_holders h USING (policy_no) JOIN policy_vehicles v USING (policy_no)
               WHERE p.status = 'ISSUED' AND p.end_date = TRUNC(SYSDATE) + 30) LOOP
      INSERT INTO renewal_quotes (policy_no, ncd_years, premium, created_at)
      VALUES (p.policy_no,
              CASE WHEN p.claim_count = 0 THEN p.ncd_years + 1 ELSE 0 END,
              pkg_rating.calc_premium(p.vehicle_value, p.dob,
                                      CASE WHEN p.claim_count = 0 THEN p.ncd_years + 1 ELSE 0 END),
              SYSTIMESTAMP);
    END LOOP;
  END create_renewal_quotes;
END pkg_renewal;
/
