package com.example.motor.claims;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.*;

class FnolServiceTest {

    private final Fixtures fx = Fixtures.issuedPolicy("MOT-2026-000123",
            LocalDate.of(2026, 1, 1), LocalDate.of(2026, 12, 31));

    // Verifies: TC-009
    @Test
    void rejectsALossDateOutsideThePolicyPeriod() {
        assertThatThrownBy(() -> fx.service().register(fx.claimOn(LocalDate.of(2027, 1, 2)), false))
                .hasMessage("Loss date is outside an issued policy period");
    }

    // Verifies: TC-011
    @Test
    void duplicateNeedsConfirmation() {
        fx.service().register(fx.claimOn(LocalDate.of(2026, 6, 1)), false);
        assertThatThrownBy(() -> fx.service().register(fx.claimOn(LocalDate.of(2026, 6, 1)), false))
                .isInstanceOf(PossibleDuplicateException.class);
        assertThatNoException().isThrownBy(() -> fx.service().register(fx.claimOn(LocalDate.of(2026, 6, 1)), true));
    }
}
