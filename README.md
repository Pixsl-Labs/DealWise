# DealWise

Desktop marketplace intelligence platform for tracking hardware deals, analysing prices, and detecting potential scams.

DealWise is a Linux-first GTK4 desktop application designed to run quietly in the background and surface useful marketplace deals without constant manual searching.

## Current Status

Version: `0.1.0`

Phase 1 foundation is in progress.

Implemented so far:

- GTK4 desktop application shell
- Dark desktop UI
- Sidebar navigation
- Dashboard
- Saved search creation
- Local config directory
- Background refresh scheduler stub
- Runtime logging
- Documentation foundation

Marketplace scraping is not implemented yet. The current search manager is intentionally a safe scheduler foundation ready for future marketplace plugins.

## Planned Features

- Vinted marketplace support
- eBay support
- Saved listings
- Desktop notifications
- Deal score
- Scam score
- Reverse image search
- Price history
- Build planner
- Marketplace plugin system

## Linux Requirements

DealWise currently uses GTK4 through system packages.

On Linux Mint / Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-gi gir1.2-gtk-4.0
```