package com.example.orders.pricing;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Line totals with the volume discount from PKG_ORDER_PRICING.
 * Implements LLD-002.
 */
@Component
public class DiscountCalculator {

    static final int VOLUME_THRESHOLD = 100;
    static final BigDecimal VOLUME_FACTOR = new BigDecimal("0.90");

    public BigDecimal lineTotal(int qty, BigDecimal unitPrice) {
        BigDecimal gross = unitPrice.multiply(BigDecimal.valueOf(qty));
        if (qty >= VOLUME_THRESHOLD) {
            gross = gross.multiply(VOLUME_FACTOR);
        }
        return gross.setScale(2, RoundingMode.HALF_UP);
    }
}
