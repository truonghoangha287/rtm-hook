package com.example.motor.rating;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Annual premium, replacing pkg_rating.calc_premium. Pure: no I/O.
 * Implements LLD-002.
 */
@Component
public class PremiumCalculator {

    private final RatingFactors f;

    public PremiumCalculator(RatingFactors factors) {
        this.f = factors;
    }

    public BigDecimal annualPremium(BigDecimal vehicleValue, int ageAtStart, int ncdYears) {
        BigDecimal premium = vehicleValue.multiply(f.baseRate());
        if (ageAtStart < f.youngAgeBelow()) {
            premium = premium.multiply(f.youngLoading());
        }
        BigDecimal ncd = f.ncdPerYear().multiply(BigDecimal.valueOf(ncdYears)).min(f.ncdMax());
        premium = premium.multiply(BigDecimal.ONE.subtract(ncd));
        return premium.max(f.minimumPremium()).setScale(2, RoundingMode.HALF_UP);
    }
}
