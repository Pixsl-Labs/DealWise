# Changelog

## [0.6.2] - 2026-07-10

### Fixed

- Added Vinted cooldown after HTTP 429 rate limits.
- Limited manual refresh to 3 saved searches at a time to avoid rate limiting.
- Fixed saved/favourited deals ignoring Live Deals filters.
- Fixed price history pollution where full PCs containing CPU names were counted as CPU price history.
- Fixed repeated refreshes counting the same listing many times in price history.
- Added outlier trimming to observed price history.

### Added

- Clear Filters button in Live Deals.

### Notes

- README intentionally not changed.
- Price history is still local observed DealWise history, not completed-sales data yet.

## [0.6.1] - 2026-07-10

### Added

- Stop Searching status for PC Builder checklist parts.
- Parts marked Stop Searching are skipped by Search Needed Parts.
- Global laptop/notebook blocking for live marketplace results.

### Fixed

- Blocked laptop-style listings such as Zenbook, ThinkPad, MacBook, Chromebook and notebooks from appearing as PC part deals.
- Applied blocked/excluded keyword filtering before storing marketplace results.

### Notes

- README intentionally not changed.
- Existing laptop listings are removed from the local DealWise database by this update.

## [0.6.0] - 2026-07-10

### Added

- Phase 6 price history storage using observed marketplace listing snapshots.
- Price history lines on live and saved listing cards.
- Deal score adjustment using observed DealWise price history.
- Live Deals search box.
- Live Deals Apply Filters button.
- Full PC / PC parts priority sorting.
- Rule-based compatibility service for CPU, motherboard, RAM, PSU, GPU, case and Linux Mint GPU preference.
- Selected parts compatibility card in PC Builder.
- Listing-level compatibility notes.

### Fixed

- Added safer startup fatal logging.
- Added SQLite migrations for price history and older local databases.
- Reduced image flicker by avoiding connector-status-only row rebuilds.

### Notes

- README intentionally not changed.
- Phase 6 learns from listings DealWise has seen. Completed-sales marketplace history is still future work.

## [0.4.5] - 2026-07-10

### Added

- Hardware Preference selector in PC Builder.
- Linux Mint friendly AMD-first recommendation path.
- Live Deals Show First selector for PC parts or full PCs.
- Apply Filters button in Live Deals.
- Full PC detection for filtering and priority sorting.
- More price-aware deal scoring.

### Fixed

- Reduced Live Deals image flicker by avoiding status-only list redraws.
- Added instant thumbnail loading from local image cache.
- Prevented filter controls from rebuilding the list on every small change.

### Notes

- README intentionally not changed.
- Deal scores are still local rough estimates, not full price-history scoring yet.

## [0.4.4] - 2026-07-10

### Fixed

- Added SQLite schema migrations for older local DealWise databases.
- Moved heavy startup refreshes to safe delayed startup so the window can appear first.
- Added safe periodic refresh wrappers.
- Added fatal startup logging to /tmp/dealwise_fatal.log.

### Notes

- README intentionally not changed.
- Existing runtime database is preserved unless SQLite reports corruption.

## [0.4.3] - 2026-07-10

### Fixed

- Fixed startup failure caused by missing PCBuilderService.estimate_build_cost.
- Fixed Apply Recommendations so selected parts also receive sensible budgets.
- Prevented selected build cost overview from calling a missing service method.

### Notes

- README intentionally not changed.

## [0.4.2] - 2026-07-10

### Added

- Live Deals filter and sorting controls.
- Focus filter for all deals vs checklist matches.
- Part type filter.
- Max price filter.
- High scam risk toggle.
- Build cost overview in PC Builder.
- Clearer Current PC Snapshot display.
- Clearer resale valuation display.
- More high-end CPU, GPU, motherboard, RAM, PSU, case and cooling options.
- Rough selected build cost estimates.

### Changed

- Live Deals now skips redraws when content has not changed to reduce lag and image flicker.
- Target Build Summary updates live when controls change.
- Search Plan updates live when controls change.
- Notes area is larger and clearer.
- Part budgets are no longer left at £0 for Storage and Cooling.
- CPU, motherboard and RAM options are more strictly filtered by build path.

### Notes

- README intentionally not changed.
- Compatibility remains rule-based and local, not a full hardware database yet.

## [0.4.1] - 2026-07-10

### Added

- Visible Live Deals card layout.
- Remove button for live listings.
- Remove button for stored/saved listings.
- Persisted open/closed state for Live Deals sections.
- Phase 6 through Phase 14 planning documents.

### Changed

- Individual listings are no longer collapsible expanders.
- Only Saved / Favourited Deals and New / Worth Checking are collapsible.
- Live deal rows now show decision, scores, reasoning, URL, image area, and actions immediately.

### Notes

- README intentionally not changed.
- Full future phases are documented as foundations, not claimed as production-complete.

## [0.4.0] - 2026-07-10

### Added

- Phase 4 deal/scam scoring foundation in Live Deals.
- Phase 5 image-check foundation using marketplace listing image URLs.
- Build path-aware part compatibility catalog.
- Use Case dropdown.
- Build Path dropdown.
- Expandable target build notes.
- Apply Recommendations action.
- Search Needed Parts action.
- Compatible part dropdowns in the parts checklist.
- Collapsible Saved / Favourited Deals section.
- Collapsible New / Worth Checking section.
- Listing thumbnails where image URLs are available.
- Favourite saved-listing status.
- Named desktop icon install support.

### Changed

- Live Deals now prioritises listings that match the current parts checklist.
- PC Builder is clearer and more decision-led.
- Desktop launcher now uses Icon=dealwise for better Linux icon-theme behaviour.

### Notes

- README intentionally not changed.
- Compatibility rules are a static local foundation, not a full compatibility database yet.
- Reverse image search is still manual image-check foundation only.

## [0.3.2] - 2026-07-10

### Added

- Updated DealWise app icon.
- Clear Saved PC button on the PC Builder page.
- Rough current PC resale valuation.
- Whole-unit resale estimate.
- Separate-parts resale estimate.
- Valuation confidence and notes.

### Changed

- PC Builder current PC import flow now surfaces estimated resale value after specs are provided.

### Notes

- README intentionally not changed.
- Valuation is an offline heuristic and not live marketplace pricing yet.

## [0.3.1] - 2026-07-10

### Added

- Linux-first current PC import window.
- Copyable inxi -Fx command.
- Manual paste workflow for importing PC specs.
- Clear pasted import text action.
- Clear saved current PC profile action.

### Changed

- Import Current PC now opens a transparent command/paste workflow instead of silently running inxi.

### Notes

- README intentionally not changed.
- Automatic inxi parsing service remains available internally.

## [0.3.0] - 2026-07-09

### Added

- SQLite database initialisation.
- Persistent listing repository.
- Durable listing deduplication.
- Saved Listings page.
- PC Builder page.
- Current PC import using inxi -Fx.
- Target build budget and platform fields.
- Parts checklist foundation.
- Listing Checker page.
- Manual listing save flow.
- Buy decision placeholder.
- Deal/scam/build/budget/evidence placeholder scoring.
- Seller message generator.
- Phase 3 planning status update.

### Notes

- README intentionally not changed during Phase 3 activation.
- Advanced scoring remains explainable placeholder logic.
- Marketplace login and buying automation remain non-goals.

All notable changes to DealWise will be documented in this file.

## [0.2.0] - 2026-07-09

### Added

- Marketplace connector package.
- Base marketplace connector interface.
- Marketplace registry.
- Vinted public search connector.
- Normalised marketplace listing model.
- Marketplace search result model.
- Asynchronous saved-search refresh worker.
- Randomised saved-search refresh jitter.
- In-memory live result deduplication.
- Live Deals page implementation.
- Open listing button.
- Connector status display on dashboard and Live Deals page.
- Phase 2 documentation.

### Changed

- Updated app version to 0.2.0.
- Updated search manager from placeholder scheduler to connector dispatcher.
- Updated README for Phase 2.
- Updated roadmap status for Phase 2.

### Notes

- Vinted connector is best-effort and public-search only.
- No marketplace credentials are required or stored.
- Phase 3 should add SQLite persistence, durable deduplication, and notifications.

## [0.1.0] - 2026-07-09

### Added

- Initial GTK4 desktop application scaffold.
- Main application entry point.
- Dark themed main window.
- Sidebar navigation.
- Dashboard page.
- Saved Searches page.
- Saved search persistence under ~/.config/Pixsl-Labs/DealWise/searches.json.
- Local configuration directory under ~/.config/Pixsl-Labs/DealWise/.
- Background search refresh scheduler stub.
- Runtime logging to ~/.config/Pixsl-Labs/DealWise/logs/dealwise.log.

### Notes

- Marketplace scraping was not implemented yet.
