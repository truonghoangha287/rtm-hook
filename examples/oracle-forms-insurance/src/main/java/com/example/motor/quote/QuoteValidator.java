package com.example.motor.quote;

import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.LocalDate;
import java.time.Period;

/**
 * Holder age and cover period rules from the POLICY_ISSUE WHEN-VALIDATE-ITEM triggers.
 * Implements LLD-001.
 */
@Component
public class QuoteValidator {

    private final Clock clock;

    public QuoteValidator(Clock clock) {
        this.clock = clock;
    }

    public void validate(QuoteRequest q) {
        if (q.startDate().isBefore(LocalDate.now(clock))) {
            throw new QuoteRejectedException("Cover cannot start in the past");
        }
        if (Period.between(q.holder().dateOfBirth(), q.startDate()).getYears() < 18) {
            throw new QuoteRejectedException("Policy holder must be at least 18 on the start date");
        }
        if (q.covers().isEmpty()) {
            throw new QuoteRejectedException("At least one cover is required");
        }
    }

    public LocalDate endDate(LocalDate start) {
        return start.plusMonths(12).minusDays(1);
    }
}
