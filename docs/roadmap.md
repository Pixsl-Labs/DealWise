# DealWise Roadmap

Version: Project Roadmap v1  
Author: Sam  
Repository: Pixsl-Labs / DealWise  
Platform: Linux Mint first, Windows future  
UI: GTK4 Desktop Application  
Language: Python  

---

# Roadmap Philosophy

DealWise should be developed incrementally.

The project should avoid large rewrites unless explicitly requested.

Every phase should preserve existing functionality and extend the application in a clean, modular way.

The goal is not just to make the app work.

The goal is to build a production-quality Pixsl-Labs desktop application that could realistically be released publicly.

---

# Core Development Rules

- Preserve existing functionality.
- Extend instead of rewriting.
- Keep UI, services, data storage, and marketplace logic separate.
- Keep marketplace connectors modular.
- Keep credentials out of project files.
- Store runtime user data outside the repository.
- Prefer logging over print statements.
- Update documentation when meaningful features are added.
- Keep the app useful even before marketplace login support exists.

---

# Credential Strategy

## Current Decision

Marketplace login credentials are not required for the early versions of DealWise.

The first real versions should focus on:

- Public marketplace searching
- Local saved searches
- Local saved listings
- Local watchlist
- Local notes
- Price tracking
- Deal scoring
- Scam scoring
- Opening listing URLs in the browser

DealWise should save items inside its own local database before trying to save items inside marketplace accounts.

This avoids:

- Fragile login automation
- Account/session handling
- Plain-text password risk
- Marketplace account issues
- Sensitive data being stored too early
- Larger security burden before it is needed

## What Works Without Login

DealWise can support the following without storing marketplace passwords:

- Public listing search
- Listing URL collection
- Price tracking
- Local saved listings
- Local watchlist
- Local notes
- Tags and priority labels
- Deal scoring
- Scam scoring
- Reverse image checks
- Browser handoff for buying or messaging manually
- Notifications when matching listings appear

## What Might Need Login Later

Login may only become useful for:

- Saving/favouriting items inside a marketplace account
- Messaging sellers
- Reading account-specific watchlists
- Syncing marketplace favourites
- Accessing account-only listings

## Where Credentials Must Be Stored Later

Credentials must never be stored in:

```text
.secret
.env
config.json
searches.json
plain JSON
plain text
project folders
Git-tracked files
```

Future credential storage should use the operating system credential manager.

Linux:

```text
Secret Service / GNOME Keyring / libsecret
```

Windows:

```text
Windows Credential Manager
```

Likely future Python package:

```text
keyring
```

Safe app data should live in:

```text
~/.config/Pixsl-Labs/DealWise/
├── config.json
├── searches.json
├── database/
├── images/
├── cache/
└── logs/
```

Sensitive credentials should live outside those files in the OS keyring.

## Future Credential Flow

1. User opens Settings.
2. User selects marketplace account integration.
3. DealWise asks for username/email.
4. DealWise stores the secret using the OS keyring.
5. DealWise stores only non-sensitive metadata in config.
6. DealWise never prints or logs credentials.
7. DealWise provides a remove credentials button.
8. DealWise continues working even if credentials are missing or expired.

---

# Phase 0 — Planning and Repository Setup

Status: Complete / In Progress

## Goal

Create the project foundation and define the product direction.

## Deliverables

- GitHub repository.
- MIT licence.
- README.
- Project planning document.
- Roadmap.
- Architecture documentation.
- Clear security rules.
- Linux-first GTK4 decision.
- Python application direction.

## Success Criteria

- Repository is clean.
- No nested Git repo issue.
- No credentials are committed.
- Project has a clear vision.
- Initial documentation explains what DealWise is trying to become.

---

# Phase 1 — GTK4 Application Foundation

Status: In Progress

## Goal

Create the first working DealWise desktop application.

## Deliverables

- GTK4 desktop window.
- Dark UI.
- Sidebar navigation.
- Dashboard page.
- Saved Searches page.
- Settings page.
- Logs page.
- About page.
- Placeholder pages for future features.
- Local config directory.
- Saved search JSON storage.
- Background refresh scheduler stub.
- Logging system.
- Documentation updates.

## Current Pages

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

## Success Criteria

- App launches with `python3 main.py`.
- Sidebar navigation works.
- Saved searches can be created.
- Saved searches can be deleted.
- Saved searches persist after restart.
- Runtime logs are created outside the repo.
- No marketplace scraping yet.
- No credentials required.

---

# Phase 1.5 — Local Saved Listings and Watchlist Foundation

Status: Next Recommended Phase

## Goal

Allow DealWise to save items locally before connecting real marketplace search.

This makes the app useful before scraping and creates the data model that marketplace results can reuse later.

## Deliverables

- Saved listing model.
- Local saved listings storage.
- Watchlist page implementation.
- Manual add listing form.
- Delete saved listing.
- Open listing in browser.
- Listing notes.
- Listing tags.
- Listing priority.
- Basic compare-ready data structure.
- Documentation update.

## Suggested Early Storage

```text
~/.config/Pixsl-Labs/DealWise/database/listings.json
```

## Future Storage

```text
~/.config/Pixsl-Labs/DealWise/database/dealwise.db
```

## Saved Listing Fields

```text
id
title
price
currency
marketplace
url
seller_name
condition
location
notes
tags
priority
date_found
date_saved
status
```

## Success Criteria

- User can manually save a listing.
- User can open the listing URL from DealWise.
- Saved listings persist after restart.
- Watchlist page is no longer a placeholder.
- No marketplace login required.

---

# Phase 2 — Marketplace Connector Interface and Vinted Public Search

Status: Planned

## Goal

Add the first real marketplace connector using public search behaviour.

Vinted should be the first target because it is useful for hardware deal hunting and does not need login for basic public search.

## Deliverables

- Marketplace connector interface.
- Vinted connector.
- Search request builder.
- Listing parser.
- Listing result model.
- Basic result display in Live Deals.
- Search refresh integration.
- Error handling.
- Rate limiting.
- Randomised refresh jitter.
- Connector status logging.
- User-agent configuration if needed.

## Important Rules

- Do not use login credentials yet.
- Do not automate purchases.
- Do not message sellers.
- Do not scrape aggressively.
- Do not hardcode marketplace logic inside the UI.
- Do not let connector failures crash the whole app.

## Success Criteria

- Saved search can trigger a Vinted public search.
- Results appear in Live Deals.
- Results include title, price, URL, marketplace, and image URL if available.
- Duplicate listings are not repeatedly shown as new.
- Connector failures are logged and handled safely.

---

# Phase 3 — Listing Database, Deduplication and Notifications

Status: Planned

## Goal

Move from temporary marketplace results into persistent marketplace intelligence.

## Deliverables

- SQLite database.
- Listing repository layer.
- Search result history.
- Deduplication by marketplace and listing ID or URL.
- First seen timestamp.
- Last seen timestamp.
- Removed listing detection.
- Desktop notifications.
- Notification history.
- New listing alerts.
- Price change alerts.
- Listing removed alerts.

## Suggested Database

```text
~/.config/Pixsl-Labs/DealWise/database/dealwise.db
```

## Success Criteria

- New listings are stored.
- Duplicate listings are ignored or updated.
- New deal notifications work.
- Price changes can be detected.
- Database survives app restarts.

---

# Phase 4 — Deal Score and Scam Score

Status: Planned

## Goal

Turn raw marketplace listings into useful buying decisions.

## Deal Score

Range:

```text
0-100
```

Example labels:

```text
90-100 Excellent Deal
75-89 Very Good
55-74 Fair
35-54 Weak
0-34 Avoid
```

Factors:

- Price
- Condition
- Shipping cost
- Seller rating
- Listing age
- Historical average
- Demand
- Availability
- Keyword quality

## Scam Score

Range:

```text
0-10
```

Example labels:

```text
0-2 Low Risk
3-5 Use Caution
6-8 High Risk
9-10 Avoid
```

Factors:

- Price too low
- New seller
- No feedback
- Missing product details
- Generic wording
- Suspicious wording
- Repeated listings
- Copied images
- Location mismatch
- External payment pressure

## Success Criteria

- Every listing can receive a deal score.
- Every listing can receive a scam score.
- Scoring explanation is visible to the user.
- Scoring rules are configurable and not scattered across the app.

---

# Phase 5 — Reverse Image Search Foundation

Status: Planned

## Goal

Add the flagship suspicious-listing investigation feature.

## Deliverables

- Manual image upload.
- Drag and drop image support.
- Paste image from clipboard.
- Image storage/cache.
- Reverse image result model.
- Reverse image page implementation.
- Side-by-side image comparison UI.
- Basic external reverse image search handoff.
- Link reverse image result into scam scoring.

## Early Safe Approach

The first version can open the selected image or image URL in the browser with supported reverse image search services.

Later versions can add deeper automated result parsing if reliable and allowed.

## Success Criteria

- User can manually check a listing image.
- User can store reverse image results locally.
- Scam score can consider reverse image result status.
- No credentials required.

---

# Phase 6 — Price History and Graphs

Status: Planned

## Goal

Show whether a deal is genuinely good based on historical prices.

## Deliverables

- Price history storage.
- Listing snapshots.
- Product grouping.
- 30 day trend.
- 90 day trend.
- 180 day trend.
- 1 year trend.
- Average price.
- Median price.
- Lowest seen price.
- Highest seen price.
- Graph UI.
- Deal score integration.

## Success Criteria

- DealWise can show whether a current listing is above or below average.
- User can view historical prices for a product/search.
- Deal score can use historical pricing.

---

# Phase 7 — Additional Marketplace Connectors

Status: Planned

## Goal

Expand beyond Vinted while keeping connectors modular.

## Planned Connectors

- eBay
- Gumtree
- CeX
- Facebook Marketplace
- Amazon
- Ebuyer
- Scan
- Overclockers UK
- AWD-IT
- Currys Clearance
- Box
- PC Specialist Outlet

## Connector Rules

Each connector should provide:

```text
name
search()
parse_listing()
normalise_price()
extract_listing_id()
fetch_images()
seller_info_if_available()
```

## Success Criteria

- Connectors are modular.
- A broken connector does not break the full app.
- Each marketplace can be enabled or disabled.
- Saved searches can target one or multiple marketplaces.

---

# Phase 8 — Compare Listings

Status: Planned

## Goal

Allow users to compare multiple possible purchases side-by-side.

## Deliverables

- Compare selected listings.
- Compare price.
- Compare marketplace.
- Compare seller.
- Compare condition.
- Compare shipping.
- Compare total cost.
- Compare deal score.
- Compare scam score.
- Compare reverse image status.
- Compare notes.

## Success Criteria

- User can select multiple saved/live listings.
- Comparison view makes the best option obvious.
- Comparison uses the same listing model as saved listings and marketplace results.

---

# Phase 9 — Build Planner

Status: Planned

## Goal

Connect deal hunting to actual PC upgrade planning.

## Deliverables

- Current build profile.
- Target build profile.
- Component checklist.
- Needed parts list.
- Completed parts list.
- Estimated cost remaining.
- Best current deal per part.
- Compatibility notes.
- Performance per pound.

## Example Current Build

```text
Dell Precision 3420 SFF
Intel i7-7700
RX 6400 Low Profile
16GB DDR4
512GB NVMe
```

## Example Target Build

```text
Ryzen 7700
RX 6800 / RX 7700 XT
32GB DDR5
B650
2TB NVMe
```

## Success Criteria

- User can define current and target builds.
- DealWise can link saved searches to target parts.
- Dashboard can show progress towards target build.

---

# Phase 10 — AI Deal Assistant

Status: Planned

## Goal

Add natural-language deal summaries and recommendations.

## Deliverables

- Listing summary.
- Buy / wait / negotiate / avoid recommendation.
- Explanation panel.
- Risk explanation.
- Deal explanation.
- Optional local/offline mode if possible.
- Optional cloud AI integration if user configures it.

## Example Output

```text
This listing appears promising.

The price is below the recent average, the seller has acceptable feedback, and no obvious scam indicators were found.

Recommended action: negotiate.
```

## Success Criteria

- AI summaries never hide raw evidence.
- User can see the reasoning factors.
- AI features are optional.
- No API keys are committed to Git.

---

# Phase 11 — Credential and Authenticated Marketplace Support

Status: Future / Optional

## Goal

Only add login support if DealWise genuinely needs authenticated marketplace actions.

## Possible Features

- Save item to marketplace account.
- Read marketplace watchlist.
- Sync marketplace favourites.
- Message seller draft handoff.
- Account-specific alerts.

## Required Security

- Store secrets only in OS credential manager.
- Never log secrets.
- Never commit secrets.
- Provide remove credentials button.
- Handle expired sessions safely.
- Allow app to work without login.

## Linux Storage

```text
Secret Service / GNOME Keyring
```

Likely Python package:

```text
keyring
```

## Windows Storage

```text
Windows Credential Manager
```

## Success Criteria

- App works without credentials.
- Credentials are optional.
- Credentials never appear in project files.
- Credentials can be deleted from the app.

---

# Phase 12 — Packaging and Desktop Integration

Status: Planned

## Goal

Make DealWise feel like a real Linux desktop application.

## Deliverables

- Desktop entry file.
- App icon.
- Cinnamon panel friendly launch behaviour.
- Autostart option.
- System tray or background indicator.
- Notification integration.
- Release script.
- Install script.
- AppImage investigation.
- Flatpak investigation.

## Success Criteria

- User can launch DealWise from the app menu.
- User can pin DealWise to Cinnamon panel.
- User can enable startup on login.
- Logs and config remain outside the project folder.

---

# Phase 13 — Production Hardening

Status: Planned

## Goal

Make DealWise reliable enough for public release.

## Deliverables

- Unit tests.
- Integration tests.
- Connector tests.
- UI smoke tests.
- Error reporting.
- Better logging viewer.
- Settings import/export.
- Database migration system.
- Backup/restore.
- Performance profiling.
- Memory usage checks.
- Rate-limit controls.
- Documentation polish.

## Success Criteria

- App can run for long periods without crashing.
- Broken marketplace responses are handled safely.
- User data survives upgrades.
- Public README explains install, run, and security model.

---

# Phase 14 — LifeWise Integration

Status: Future

## Goal

Allow DealWise to become part of the wider LifeWise ecosystem.

## Possible Integrations

MoneyWise:

- Track purchases.
- Compare planned spend against budget.
- Show affordability.

TaskWise:

- Create shopping reminders.
- Follow up on watched items.

GoalWise:

- Link deal hunting to savings goals.
- Track progress towards a target build.

MacroWise:

- Not directly related, but can sit under the same LifeWise launcher/dashboard.

## Success Criteria

- DealWise remains useful standalone.
- LifeWise integration is optional.
- No tight coupling between apps.

---

# Current Recommended Next Steps

## Immediate

1. Finish Phase 1 testing.
2. Commit Phase 1.
3. Add this roadmap.
4. Add Phase 1.5 local saved listings/watchlist.
5. Then move to Phase 2 Vinted public search.

## Why Phase 1.5 Before Phase 2

Local saved listings are useful before scraping.

They also create the correct data model for marketplace results later.

When Vinted results arrive, they can reuse the same listing model and saved listing UI instead of requiring a rewrite.

---

# Suggested Commit Messages

For this roadmap:

```text
docs: add DealWise development roadmap
```

For saved listings:

```text
feat: add local saved listings
```

For Vinted public search:

```text
feat: add Vinted public search connector
```

For secure credential/keyring support later:

```text
feat: add secure credential storage
```
