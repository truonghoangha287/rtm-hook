package com.example.orders.order;

import com.example.orders.credit.CreditCheckService;
import com.example.orders.pricing.DiscountCalculator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

/**
 * Saves an order header and its lines in one transaction, after the credit check.
 * Implements LLD-001.
 */
@Service
public class OrderService {

    private final OrderRepository repository;
    private final CreditCheckService creditCheck;
    private final DiscountCalculator pricing;

    public OrderService(OrderRepository repository, CreditCheckService creditCheck, DiscountCalculator pricing) {
        this.repository = repository;
        this.creditCheck = creditCheck;
        this.pricing = pricing;
    }

    @Transactional
    public OrderDto create(OrderDto request) {
        if (request.lines().isEmpty()) {
            throw new IllegalArgumentException("An order needs at least one line");
        }
        BigDecimal total = request.lines().stream()
                .map(l -> pricing.lineTotal(l.qty(), l.unitPrice()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        creditCheck.assertWithinLimit(request.customerId(), total);
        return repository.save(request.withTotal(total));
    }
}
