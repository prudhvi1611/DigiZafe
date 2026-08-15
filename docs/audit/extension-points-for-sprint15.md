# Sprint 15 Extension Points

This document highlights how Sprint 15 (Verified Identity Anchor) will securely extend the Sprint 13 baseline without modifying stable core systems.

## Where should Identity Anchor live?
The `Identity Anchor` should live in `app.services.identity_graph`. It should NOT be a separate table from the graph; it is a specialized, high-confidence graph node (`node_type="anchor"`).

## Should it extend or reference verified identifiers?
It must reference the `Identifier` table via foreign key (or deterministic graph edge), ensuring that an anchor cannot exist without a verified `is_verified=True` identifier. 

## Where should user-confirmed aliases live?
Confirmed aliases should live in the Identity Graph as standard nodes, connected to the anchor via `confirmed_alias` edges. 

## How should deletion cascade?
When a user deletes their account, the `User` cascade will drop the `Identifier`. Any graph nodes linked directly to the `Identifier` or `User` must drop via standard ON DELETE CASCADE rules configured in SQLAlchemy, triggering crypto-shredding on the blob store if any evidence fragments exist.

## Which contracts must Sprint 15 reuse?
Sprint 15 MUST reuse:
- The existing `app.domain.exposure` enums.
- The `app.services.discovery_service.DiscoveryService` for orchestrating deep candidate discovery.
- The `app.services.consent_service.ConsentService` to gate OSINTgram/Maigret network activity.
