package com.example.motor.quote;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

/**
 * Replaces the POLICY_ISSUE form's quote capture.
 * Implements LLD-001.
 */
@RestController
@RequestMapping("/quotes")
public class QuoteController {

    private final QuoteValidator validator;
    private final QuoteRepository quotes;

    public QuoteController(QuoteValidator validator, QuoteRepository quotes) {
        this.validator = validator;
        this.quotes = quotes;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Quote create(@RequestBody QuoteRequest request) {
        validator.validate(request);
        return quotes.save(Quote.from(request, validator.endDate(request.startDate())));
    }
}
