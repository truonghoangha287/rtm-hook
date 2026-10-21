package com.example.motor.underwriting;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * Referral rules from pkg_underwriting.needs_referral.
 * Implements LLD-003.
 */
@Component
public class UnderwritingRules {

    static final BigDecimal HIGH_VALUE = new BigDecimal("100000");
    static final int MIN_LICENCE_YEARS = 2;

    public boolean needsReferral(BigDecimal vehicleValue, int licenceYears) {
        return vehicleValue.compareTo(HIGH_VALUE) > 0 || licenceYears < MIN_LICENCE_YEARS;
    }
}
