# DealWise

Desktop marketplace intelligence platform for tracking hardware deals, analysing prices, and detecting potential scams.

DealWise is a Linux-first GTK4 desktop application designed to run quietly in the background and surface useful marketplace deals without constant manual searching.

## Current Status

Version: 0.2.0

Phase 2 foundation is implemented.

Implemented so far:

- GTK4 desktop application shell
- Dark desktop UI
- Sidebar navigation
- Dashboard
- Saved search creation
- Local config directory
- Background refresh scheduler
- Runtime logging
- Marketplace connector interface
- Vinted public search connector
- Live Deals result page
- In-memory result deduplication for the current session
- Documentation foundation

## Marketplace Support

Current connector:

- Vinted public search

Not implemented yet:

- eBay
- Gumtree
- CeX
- Facebook Marketplace
- Amazon
- Scan
- Ebuyer
- Overclockers UK

## Important Marketplace Notes

DealWise does not use marketplace login credentials yet.

The Vinted connector is best-effort and public-search only. It does not:

- Log in
- Save to a marketplace account
- Message sellers
- Buy items
- Store credentials
- Automate private account actions

Vinted may change or block public/internal endpoints. If that happens, DealWise should log the connector failure rather than crash.

## Planned Next Phase

Phase 3 will add:

- SQLite listing database
- Persistent deduplication
- Listing repository layer
- Notification history
- New listing alerts
- Price change alerts
- Removed listing detection

## Linux Requirements

DealWise currently uses GTK4 through system packages.

On Linux Mint / Ubuntu:

    sudo apt update
    sudo apt install -y python3-gi gir1.2-gtk-4.0

No pip packages are required for Phase 2.

## Run

From the project root:

    python3 main.py

## Local Data

DealWise stores runtime data outside the Git repository:

    ~/.config/Pixsl-Labs/DealWise/
    ├── config.json
    ├── searches.json
    ├── cache/
    ├── images/
    ├── logs/
    └── database/

Logs are stored at:

    ~/.config/Pixsl-Labs/DealWise/logs/dealwise.log

## Security Rules

Do not store marketplace credentials in the project folder.

Future credential support should use:

- Linux Secret Service / Keyring
- Windows Credential Manager

Never commit secrets, cookies, tokens, sessions, or account credentials to Git.

## Development Principles

- Preserve existing functionality
- Extend instead of rewriting
- Keep code modular
- Keep UI separate from services
- Keep marketplace logic in plugins/connectors
- Store user runtime data outside the repository
- Prefer logging over print statements

## Repository

Pixsl-Labs / DealWise
