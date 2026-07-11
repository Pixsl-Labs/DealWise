# DealWise Phase 7 Readiness

## Status

Ready to start Phase 7 carefully, but one connector at a time.

## Current Position

DealWise now has:

- A marketplace connector interface.
- A marketplace registry.
- Safe connector error handling.
- Vinted public search.
- SQLite persistence.
- Price history snapshots.
- Product-aware filtering.
- Buyer evidence checks.
- Rate-limit cooldown behaviour.

## Remaining Risk Before Many Connectors

- Vinted is still best-effort and can rate-limit.
- Saved searches currently target one marketplace at a time.
- Product grouping is rule-based.
- Reverse image search is still a manual handoff.
- No test suite exists yet.

## Recommended Phase 7 Order

1. Add a read-only eBay connector if a safe/public/API route is available.
2. Add CeX pricing as a retail/reference connector.
3. Add Gumtree only after connector throttling is solid.
4. Keep Facebook Marketplace last because it is more likely to need login/browser handling.
5. Add connector health indicators before enabling many connectors at once.

## Rule

Broken connectors must never crash the whole app.
