# Changelog

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
