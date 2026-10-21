package com.example.motor.quote;

import org.junit.jupiter.api.Test;

import java.time.*;

import static org.assertj.core.api.Assertions.*;

class QuoteValidatorTest {

    private final QuoteValidator validator = new QuoteValidator(
            Clock.fixed(Instant.parse("2026-10-21T09:00:00Z"), ZoneOffset.UTC));

    // Verifies: TC-001
    @Test
    void acceptsAQuoteWithHolderVehicleAndCovers() {
        assertThatNoException().isThrownBy(() -> validator.validate(Quotes.valid()));
    }

    // Verifies: TC-002
    @Test
    void rejectsAHolderUnder18OnTheStartDate() {
        LocalDate start = LocalDate.of(2026, 11, 1);
        QuoteRequest q = Quotes.valid().withStart(start).withDateOfBirth(start.minusYears(18).plusDays(1));
        assertThatThrownBy(() -> validator.validate(q))
                .hasMessage("Policy holder must be at least 18 on the start date");
    }

    // Verifies: TC-003
    @Test
    void rejectsABackdatedStartAndRunsTwelveMonths() {
        assertThatThrownBy(() -> validator.validate(Quotes.valid().withStart(LocalDate.of(2026, 10, 20))))
                .hasMessage("Cover cannot start in the past");
        assertThat(validator.endDate(LocalDate.of(2027, 3, 1))).isEqualTo(LocalDate.of(2028, 2, 29));
    }
}
