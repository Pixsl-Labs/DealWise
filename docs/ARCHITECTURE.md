# DealWise Architecture

## Goal

DealWise should become a production-quality desktop marketplace intelligence application.

The architecture must support:

- GTK4 desktop UI
- Background search refresh
- Marketplace plugins
- Saved searches
- Saved listings
- Deal scoring
- Scam scoring
- Reverse image search
- Price history
- Build planning
- Secure credential storage

## Current Phase

Phase 2 adds marketplace connector foundations and Vinted public search.

Project structure:

    main.py
    └── dealwise/
        ├── config.py
        ├── logging_setup.py
        ├── models.py
        ├── marketplaces/
        │   ├── base.py
        │   ├── registry.py
        │   └── vinted.py
        ├── services/
        │   └── search_manager.py
        └── ui/
            ├── app.py
            └── main_window.py

## Responsibilities

### main.py

Application launcher.

### dealwise/config.py

Creates and manages the local user configuration directory.

Runtime data must live under:

    ~/.config/Pixsl-Labs/DealWise/

The project directory should remain clean and safe for Git.

### dealwise/logging_setup.py

Configures application logging.

Logs are written to:

    ~/.config/Pixsl-Labs/DealWise/logs/dealwise.log

### dealwise/models.py

Contains reusable typed data models.

Current models:

- SavedSearch
- MarketplaceListing
- MarketplaceSearchResult
- RuntimeStats

### dealwise/marketplaces/base.py

Defines the connector interface.

Connectors should:

- Accept a SavedSearch
- Return normalised MarketplaceSearchResult
- Avoid touching GTK directly
- Avoid storing credentials
- Avoid writing directly to app state

### dealwise/marketplaces/registry.py

Registers available marketplace connectors.

Current connector:

- Vinted

### dealwise/marketplaces/vinted.py

Best-effort public Vinted search connector.

Rules:

- No login
- No buying automation
- No messaging automation
- No credential storage
- Defensive error handling
- Normalise listing fields into MarketplaceListing

### dealwise/services/search_manager.py

Coordinates background saved-search refresh behaviour.

Current behaviour:

- Starts with the application
- Schedules saved searches with jitter
- Dispatches saved searches to marketplace connectors
- Runs connector searches in worker threads
- Maintains in-memory live results
- Deduplicates live results during the current session
- Updates runtime stats
- Logs connector failures safely

Future Phase 3 behaviour:

- Store results in SQLite
- Persist deduplication
- Track first seen and last seen
- Detect removed listings
- Trigger desktop notifications
- Store notification history

### dealwise/ui/app.py

GTK application object.

Owns shared services:

- Config manager
- Logger
- Search manager

### dealwise/ui/main_window.py

Main GTK4 user interface.

Current pages:

- Dashboard
- Live Deals
- Saved Searches
- Watchlist
- Price History
- Reverse Image Search
- Scam Detection
- Notifications
- Statistics
- Market Trends
- Build Planner
- Settings
- Logs
- About

## Phase 2 Search Flow

    SavedSearch
    -> SearchManager
    -> MarketplaceRegistry
    -> VintedPublicConnector
    -> MarketplaceSearchResult
    -> In-memory live result list
    -> Live Deals UI

## Phase 3 Target Flow

    SavedSearch
    -> SearchManager
    -> MarketplaceRegistry
    -> MarketplaceConnector
    -> MarketplaceSearchResult
    -> Listing Repository
    -> SQLite Database
    -> Deduplication
    -> Notifications
    -> Live Deals UI

## Security

Do not store credentials in:

- .env
- .secret
- Project folders
- Git-tracked files
- Plain JSON

Future credential support:

- Linux: Secret Service / Keyring
- Windows: Credential Manager

## Development Rules

- Do not rewrite large sections without reason.
- Add features incrementally.
- Keep UI, services, and marketplace logic separate.
- Prefer small reusable classes.
- Prefer typed models.
- Prefer logging over print statements.
- Keep documentation updated with meaningful features.
