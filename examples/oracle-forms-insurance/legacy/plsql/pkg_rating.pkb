CREATE OR REPLACE PACKAGE BODY pkg_rating AS
  c_base_rate      CONSTANT NUMBER := 0.035;  -- 3.5% of vehicle value
  c_young_loading  CONSTANT NUMBER := 1.30;   -- +30% when the holder is under 25
  c_ncd_per_year   CONSTANT NUMBER := 0.10;   -- 10% per claim-free year
  c_ncd_max        CONSTANT NUMBER := 0.50;   -- capped at 50%
  c_min_premium    CONSTANT NUMBER := 300;

  FUNCTION calc_premium(p_vehicle_value NUMBER, p_dob DATE, p_ncd_years NUMBER) RETURN NUMBER IS
    v_premium NUMBER := p_vehicle_value * c_base_rate;
  BEGIN
    IF MONTHS_BETWEEN(SYSDATE, p_dob) / 12 < 25 THEN
      v_premium := v_premium * c_young_loading;
    END IF;
    v_premium := v_premium * (1 - LEAST(NVL(p_ncd_years, 0) * c_ncd_per_year, c_ncd_max));
    RETURN ROUND(GREATEST(v_premium, c_min_premium), 2);
  END calc_premium;
END pkg_rating;
/
