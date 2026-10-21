CREATE OR REPLACE PACKAGE BODY pkg_underwriting AS
  FUNCTION needs_referral(p_vehicle_value NUMBER, p_licence_years NUMBER) RETURN BOOLEAN IS
  BEGIN
    RETURN p_vehicle_value > 100000 OR p_licence_years < 2;
  END needs_referral;
END pkg_underwriting;
/
