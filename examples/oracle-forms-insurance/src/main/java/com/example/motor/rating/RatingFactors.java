package com.example.motor.rating;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.math.BigDecimal;

/**
 * Actuarial factors bound from rating.yml (ADR-002); defaults match PKG_RATING.
 * Implements LLD-002.
 */
@ConfigurationProperties("rating")
public record RatingFactors(BigDecimal baseRate, BigDecimal youngLoading, int youngAgeBelow,
                            BigDecimal ncdPerYear, BigDecimal ncdMax, BigDecimal minimumPremium) {

    public static RatingFactors defaults() {
        return new RatingFactors(new BigDecimal("0.035"), new BigDecimal("1.30"), 25,
                new BigDecimal("0.10"), new BigDecimal("0.50"), new BigDecimal("300.00"));
    }
}
