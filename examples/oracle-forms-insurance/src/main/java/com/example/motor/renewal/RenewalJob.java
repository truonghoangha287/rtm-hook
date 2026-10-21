package com.example.motor.renewal;

import com.example.motor.rating.PremiumCalculator;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.LocalDate;

/**
 * Nightly renewal quotes, replacing pkg_renewal.create_renewal_quotes.
 * Implements LLD-007.
 */
@Component
public class RenewalJob {

    private final RenewalRepository repository;
    private final PremiumCalculator rating;
    private final Clock clock;

    public RenewalJob(RenewalRepository repository, PremiumCalculator rating, Clock clock) {
        this.repository = repository;
        this.rating = rating;
        this.clock = clock;
    }

    @Scheduled(cron = "0 0 2 * * *")
    public void run() {
        LocalDate expiring = LocalDate.now(clock).plusDays(30);
        for (RenewalCandidate c : repository.issuedPoliciesEndingOn(expiring)) {
            int ncd = c.claimCount() == 0 ? c.ncdYears() + 1 : 0;
            repository.saveQuote(c.policyNo(), ncd,
                    rating.annualPremium(c.vehicleValue(), c.ageAt(expiring.plusDays(1)), ncd));
        }
    }
}
