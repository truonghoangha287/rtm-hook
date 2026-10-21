package com.example.orders.order;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

/**
 * REST entry point that replaces the ORDERS form.
 * Implements LLD-001.
 */
@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderService orders;

    public OrderController(OrderService orders) {
        this.orders = orders;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OrderDto create(@RequestBody OrderDto request) {
        return orders.create(request);
    }
}
