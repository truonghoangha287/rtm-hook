package com.example.orders.pricing;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class DiscountCalculatorTest {

    private final DiscountCalculator calc = new DiscountCalculator();

    // Verifies: TC-002
    @Test
    void hundredUnitsGetTenPercentOff() {
        assertThat(calc.lineTotal(100, new BigDecimal("2.50"))).isEqualByComparingTo("225.00");
    }

    // Verifies: TC-003
    @Test
    void ninetyNineUnitsPayFullPrice() {
        assertThat(calc.lineTotal(99, new BigDecimal("2.50"))).isEqualByComparingTo("247.50");
    }
}
