package com.example.motor.underwriting;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class UnderwritingRulesTest {

    private final UnderwritingRules rules = new UnderwritingRules();

    // Verifies: TC-007
    @Test
    void refersHighValueVehiclesAndNewDrivers() {
        assertThat(rules.needsReferral(new BigDecimal("120000"), 10)).isTrue();
        assertThat(rules.needsReferral(new BigDecimal("20000"), 1)).isTrue();
        assertThat(rules.needsReferral(new BigDecimal("20000"), 5)).isFalse();
    }
}
