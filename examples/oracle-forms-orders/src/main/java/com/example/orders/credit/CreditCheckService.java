package com.example.orders.credit;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;

/**
 * Rejects an order that would take the customer's open orders over their credit limit.
 * Implements LLD-003.
 */
@Service
public class CreditCheckService {

    private final CustomerCreditRepository customers;

    public CreditCheckService(CustomerCreditRepository customers) {
        this.customers = customers;
    }

    public void assertWithinLimit(long customerId, BigDecimal newAmount) {
        BigDecimal limit = customers.creditLimit(customerId);
        BigDecimal open = customers.openOrderTotal(customerId);
        if (open.add(newAmount).compareTo(limit) > 0) {
            throw new CreditLimitExceededException("Credit limit exceeded");
        }
    }
}
