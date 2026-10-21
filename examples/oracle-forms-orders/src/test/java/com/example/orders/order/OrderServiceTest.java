package com.example.orders.order;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class OrderServiceTest {

    // Verifies: TC-001
    @Test
    void savesAnOrderWithTwoLines() {
        OrderDto saved = Fixtures.orderService().create(Fixtures.orderWithLines(2));
        assertThat(saved.lines()).hasSize(2);
    }
}
