package com.example.motor.policy;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PolicyNumberGeneratorTest {

    // Verifies: TC-008
    @Test
    void formatsProductYearAndSixDigitSequence() {
        assertThat(PolicyNumberGenerator.format("MOT", 2026, 123)).isEqualTo("MOT-2026-000123");
    }
}
