package com.example.motor.claims;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * First notice of loss, replacing the CLAIM_FNOL form.
 * Implements LLD-005; uses ClaimRouter (LLD-006).
 */
@Service
public class FnolService {

    private final PolicyLookup policies;
    private final ClaimRepository claims;
    private final ClaimRouter router;

    public FnolService(PolicyLookup policies, ClaimRepository claims, ClaimRouter router) {
        this.policies = policies;
        this.claims = claims;
        this.router = router;
    }

    @Transactional
    public Claim register(FnolRequest r, boolean confirmDuplicate) {
        PolicyPeriod p = policies.period(r.policyNo());
        if (!p.issued() || r.lossDate().isBefore(p.start()) || r.lossDate().isAfter(p.end())) {
            throw new ClaimRejectedException("Loss date is outside an issued policy period");
        }
        if (!confirmDuplicate && claims.existsByPolicyNoAndLossDate(r.policyNo(), r.lossDate())) {
            throw new PossibleDuplicateException(r.policyNo(), r.lossDate());
        }
        return claims.save(Claim.from(r, router.handlerGroup(r.estimate())));
    }
}
