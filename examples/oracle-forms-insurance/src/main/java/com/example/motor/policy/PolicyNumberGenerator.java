package com.example.motor.policy;

import org.springframework.stereotype.Component;

/**
 * Policy numbers from the existing POLICY_SEQ, as in the POLICY_ISSUE PRE-INSERT trigger.
 * Implements LLD-004.
 */
@Component
public class PolicyNumberGenerator {

    private final PolicySequence sequence;

    public PolicyNumberGenerator(PolicySequence sequence) {
        this.sequence = sequence;
    }

    public String next(String productCode, int year) {
        return format(productCode, year, sequence.nextValue());
    }

    static String format(String productCode, int year, long seq) {
        return "%s-%d-%06d".formatted(productCode, year, seq);
    }
}
