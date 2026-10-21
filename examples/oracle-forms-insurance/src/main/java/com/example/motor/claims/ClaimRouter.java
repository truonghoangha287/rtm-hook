package com.example.motor.claims;

import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * Handler routing by estimate, from the CLAIM_FNOL PRE-INSERT trigger.
 * Implements LLD-006.
 */
@Component
public class ClaimRouter {

    static final BigDecimal SENIOR_ABOVE = new BigDecimal("10000");

    public HandlerGroup handlerGroup(BigDecimal estimate) {
        return estimate.compareTo(SENIOR_ABOVE) > 0 ? HandlerGroup.SENIOR : HandlerGroup.STANDARD;
    }
}
