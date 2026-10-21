package com.example.motor.claims;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class ClaimRouterTest {

    private final ClaimRouter router = new ClaimRouter();

    // Verifies: TC-010
    @Test
    void aboveTenThousandGoesToSenior() {
        assertThat(router.handlerGroup(new BigDecimal("10000.00"))).isEqualTo(HandlerGroup.STANDARD);
        assertThat(router.handlerGroup(new BigDecimal("10000.01"))).isEqualTo(HandlerGroup.SENIOR);
    }
}
