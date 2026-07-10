# DealWise Phase 6 Plan

# Name

Price History and Product Trends

# Goal

Use stored marketplace listing snapshots to make deal scores more meaningful.

# Current Implementation

Version 0.6.0 adds:

- `price_snapshots` SQLite table.
- Product key normalisation.
- Observed lowest price.
- Observed highest price.
- Observed average price.
- Sample count.
- Price history display on Live Deals and Saved Listings.
- Deal score adjustment using observed price history.

# Important Note

This is real local DealWise history based on listings the app has seen.

It is not yet completed-sale marketplace history.

# Future Work

- Graphs.
- Completed listing imports where possible.
- Better product grouping.
- Search-specific trends.
- Price drop alerts.
- Best current deal per part.
- Price history export.
