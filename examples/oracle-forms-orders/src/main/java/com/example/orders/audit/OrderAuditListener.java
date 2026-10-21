package com.example.orders.audit;

import jakarta.persistence.PostPersist;
import jakarta.persistence.PostRemove;
import jakarta.persistence.PostUpdate;

/**
 * Writes an ORDER_AUDIT row for every order change, replacing TRG_ORDER_AUDIT.
 * Implements LLD-004.
 */
public class OrderAuditListener {

    @PostPersist
    void created(Object order) { AuditWriter.write(order, 'I'); }

    @PostUpdate
    void changed(Object order) { AuditWriter.write(order, 'U'); }

    @PostRemove
    void removed(Object order) { AuditWriter.write(order, 'D'); }
}
