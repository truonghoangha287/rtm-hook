package com.example.orders.credit;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CreditCheckServiceTest {

    // Verifies: TC-004
    @Test
    void rejectsAnOrderOverTheLimit() {
        CreditCheckService service = new CreditCheckService(
                StubCustomers.withLimit(new BigDecimal("1000"), new BigDecimal("900")));
        assertThatThrownBy(() -> service.assertWithinLimit(42L, new BigDecimal("200")))
                .isInstanceOf(CreditLimitExceededException.class)
                .hasMessage("Credit limit exceeded");
    }
}
