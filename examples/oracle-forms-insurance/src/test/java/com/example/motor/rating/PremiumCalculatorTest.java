package com.example.motor.rating;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class PremiumCalculatorTest {

    private final PremiumCalculator calc = new PremiumCalculator(RatingFactors.defaults());

    // Verifies: TC-004
    @Test
    void basePremiumIsThreeAndAHalfPercent() {
        assertThat(calc.annualPremium(new BigDecimal("20000"), 40, 0)).isEqualByComparingTo("700.00");
    }

    // Verifies: TC-005
    @Test
    void youngDriverLoadingThenNoClaimsDiscount() {
        assertThat(calc.annualPremium(new BigDecimal("20000"), 22, 3)).isEqualByComparingTo("637.00");
    }

    // Verifies: TC-006
    @Test
    void discountIsCappedAndMinimumApplies() {
        assertThat(calc.annualPremium(new BigDecimal("5000"), 40, 6)).isEqualByComparingTo("300.00");
    }
}
