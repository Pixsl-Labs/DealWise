# Changelog

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
