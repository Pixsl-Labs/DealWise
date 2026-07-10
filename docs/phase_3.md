# DealWise Phase 3 Plan

Version: Phase 3 Foundation Active
Author: Sam
Project: DealWise
Repository: Pixsl-Labs / DealWise

---

# Phase 3 Name

PC Builder, Saved Listings, Deal Intelligence and Decision Engine

---

# Phase 3 Goal

Phase 3 turns DealWise from a marketplace search tool into a PC upgrade decision engine.

The goal is to help the user:

- Import their current PC specs.
- Understand upgrade limitations.
- Build a target PC plan.
- Set a budget.
- Track needed parts.
- Save listings.
- Analyse listings.
- Check scam risk.
- Check build compatibility.
- Generate seller messages.
- Decide whether to buy, negotiate, watch, wait, or avoid.

Phase 3 should not be a giant rewrite.

It should extend the current Phase 2 foundation.

---

# Current Foundation

Phase 2 already provides:

- GTK4 desktop application.
- Sidebar navigation.
- Saved searches.
- Marketplace connector interface.
- Vinted public search connector.
- MarketplaceListing model.
- Live Deals page.
- In-memory listing results.
- App icon.
- Desktop launcher.
- Local config directory.
- Runtime logging.

Phase 3 should build on this without breaking existing functionality.

Status: Foundation implementation activated in app version 0.3.0.

---

# 10/10 Product Direction

DealWise should become:

A PC upgrade decision engine that imports your current system, builds a budget-aware upgrade plan, searches marketplaces, checks scam risk, validates compatibility, tracks saved parts, and tells you exactly whether to buy, negotiate, wait, watch, or avoid.

---

# Main Phase 3 Sections

The new PC Builder section should be structured like this:

    PC Builder
    ├── Current PC
    ├── Target Build
    ├── Budget Planner
    ├── Parts Checklist
    ├── Marketplace Search
    ├── Saved Parts
    ├── Listing Checker
    ├── Seller Message Generator
    └── Build Intelligence

The UI should feel nested and expandable.

Each deeper level should be indented visually, almost like a collapsible project tree.

---

# Section 1 — Buy Decision Engine

## Goal

Every listing should end with a clear decision, not just a score.

DealWise should recommend one of:

- Buy Now
- Negotiate
- Watch
- Wait
- Avoid

## Example

    Recommendation: Negotiate

    Why:
    + Price is below expected used market value.
    + The part matches your target build.
    + Seller appears normal.
    - Only one photo is provided.
    - No proof of working condition yet.
    - No benchmark screenshot.

    Suggested offer: £215
    Max fair price: £240
    Walk-away price: £250

## Decision Factors

The decision should consider:

- Deal score.
- Scam score.
- Build fit score.
- Budget fit score.
- Evidence confidence.
- Seller trust.
- Listing age.
- Market availability.
- Part risk level.
- Opportunity cost.

## Success Criteria

- Every listing can produce a simple recommendation.
- Recommendation is visible on listing detail view.
- Recommendation includes reasons.
- Recommendation does not hide the evidence.

---

# Section 2 — Evidence Required Before Buying

## Goal

For every part type, DealWise should tell the user what proof to request before buying.

This makes used buying safer and helps the buyer avoid awkward or unclear conversations.

## Evidence Examples

### GPU

Required evidence:

- Photo of the GPU with today's date.
- GPU-Z screenshot.
- Video or photo showing the GPU running.
- Benchmark or game test if possible.
- Close-up of ports.
- Close-up of fans.
- Confirmation of no artifacting.
- Confirmation of no overheating.
- Confirmation of mining history if known.

### CPU

Required evidence:

- Clear photo of the top of the CPU.
- Clear photo of pins or pads.
- Confirmation of no bent pins.
- Confirmation that it boots.
- Original box or proof of model if available.

### Motherboard

Required evidence:

- CPU socket close-up.
- RAM slot close-up.
- PCIe slot close-up.
- Confirmation that it boots.
- BIOS version if needed.
- I/O shield included.
- Wi-Fi antennas included if applicable.
- No damaged pins or slots.

### RAM

Required evidence:

- Clear photo of the label.
- Confirmation of capacity.
- Confirmation of speed.
- Confirmation it passes memory testing if available.

### PSU

Required evidence:

- Exact model number.
- Wattage.
- Efficiency rating.
- Cable list.
- Age.
- Warranty status.
- Confirmation it has not caused instability.
- Prefer new or trusted used only.

### Storage

Required evidence:

- SMART health screenshot.
- Total writes if available.
- Capacity.
- Model number.
- Confirmation it is not locked or faulty.

## Success Criteria

- Evidence checklist changes based on part type.
- Listing detail page shows required evidence.
- Evidence confidence can affect final decision.

---

# Section 3 — Seller Message Generator

## Goal

DealWise should generate a clear, polite message the user can send to the seller.

The message should help the buyer get proof without sounding rude or suspicious.

It should give both sides clarity and make the buyer feel safer before purchasing.

## Message Types

DealWise should generate different message styles:

- Friendly first message.
- Evidence request message.
- Negotiation message.
- Collection message.
- Shipping safety message.
- Final confirmation message.
- Walk-away message.

## Example GPU Message

    Hi, I am interested in the GPU.

    Before buying, would you be able to send a couple of extra photos please?

    Ideally:
    - A photo of the card with today's date written on paper.
    - A GPU-Z screenshot if possible.
    - A quick photo or video showing it running.
    - Confirmation it has no artifacting, overheating, or fan issues.

    Just want to check everything clearly before buying. Thanks.

## Example Negotiation Message

    Hi, thanks for the extra details.

    Based on current used prices, would you consider £215?

    I can move quickly if everything checks out.

## Example Motherboard Message

    Hi, I am interested in the motherboard.

    Could you send a clear photo of the CPU socket and confirm whether the I/O shield is included?

    Also, do you know what BIOS version it is running?

    Just checking compatibility before buying. Thanks.

## Example PSU Message

    Hi, I am interested in the PSU.

    Could you confirm the exact model, age, and which cables are included?

    Also, has it had any stability issues or warranty claims?

    Just want to be careful with power supply purchases. Thanks.

## Message Generator Inputs

The generated message should depend on:

- Part type.
- Listing risk.
- Missing evidence.
- Marketplace.
- Price.
- User's max budget.
- Whether user wants to negotiate.
- Whether the item is collection or delivery.
- Whether the seller has already provided enough information.

## Message Tone Options

The user should be able to choose:

- Friendly
- Direct
- Very cautious
- Negotiation focused
- Short and casual

## Success Criteria

- DealWise can generate a seller message from a listing.
- Message can be copied to clipboard.
- Message is specific to the part type.
- Message avoids accusing the seller.
- Message requests evidence clearly.
- Message helps the buyer feel safer.

---

# Section 4 — Upgrade Path Intelligence

## Goal

DealWise should understand whether a listing makes sense for the user's current PC and target build.

It should not just say whether the item is cheap.

It should say whether buying it is sensible.

## Example

    This RX 6800 is a strong deal, but it will not fit your current Dell SFF case.

    Recommended use:
    Save for a future ATX build, not as a current PC upgrade.

## Current PC Considerations

For the user's current Dell Precision 3420 SFF:

- Small form factor limits GPU size.
- Low-profile GPU likely required.
- PSU may be limited or proprietary.
- Motherboard is likely OEM.
- CPU platform is older.
- Heavy spending on this system may not be ideal.
- Full ATX platform upgrade may be better.

## Target Build Considerations

DealWise should check whether listings match the target build:

- CPU socket.
- Motherboard chipset.
- RAM type.
- GPU case fit.
- PSU wattage.
- PSU connectors.
- Cooler clearance.
- Storage support.
- Case form factor.

## Success Criteria

- Listing can be marked as suitable for current PC, future build, or neither.
- DealWise warns when a deal is good but incompatible.
- Compatibility notes are visible before buying.

---

# Section 5 — Build Path Locking

## Goal

Once the user chooses a build path, DealWise should protect them from buying random incompatible parts.

## Example Build Path

    AM5 Build
    CPU: Ryzen 7000 or Ryzen 9000
    Motherboard: B650 or better
    RAM: DDR5
    GPU: RX 6800 / RX 7700 XT / RX 7800 XT
    Case: ATX or mATX
    PSU: 650W or higher

## Warning Example

    Warning:
    This DDR4 motherboard does not match your locked AM5 DDR5 build path.

    Buying this may restart your build plan.

## Success Criteria

- User can lock a target platform.
- DealWise warns about incompatible saved parts.
- Locked build path affects recommendations.

---

# Section 6 — Budget Allocation

## Goal

Budget should be split by part category, not just one total number.

## Example

    Total budget: £600

    GPU: £240
    CPU: £150
    Motherboard: £100
    RAM: £60
    PSU: £50
    Case: £50
    Storage: Later

## Listing Example

    RX 6800 at £235

    GPU budget: £240
    Status: Within budget
    Remaining total budget after purchase: £365

## Success Criteria

- User can set total budget.
- User can allocate budget by part.
- Each listing can be judged against its category budget.
- Buying a part updates remaining budget.

---

# Section 7 — Opportunity Cost

## Goal

DealWise should judge listings against the whole build plan, not just individually.

## Example

    This Ryzen 7700 is a good price at £155.

    However, CPU deals appear often.
    GPU deals are rarer and usually produce larger savings.

    Recommendation:
    Watch this CPU, but prioritise GPU first.

## Success Criteria

- DealWise can recommend which deal matters most.
- DealWise can avoid pushing the user into unnecessary impulse buys.
- Opportunity cost affects Buy Now / Watch / Wait decisions.

---

# Section 8 — Part Priority and Buy Order

## Goal

DealWise should recommend what to buy first.

## Example Buy Order

    1. GPU
       Biggest price swings and best used savings.

    2. CPU
       Buy if a strong deal appears.

    3. Motherboard
       Buy with CPU to confirm compatibility.

    4. RAM
       Frequent deals, lower urgency.

    5. PSU
       Prefer new or trusted used only.

    6. Case
       Buy last unless discounted heavily.

## Success Criteria

- Target build has a suggested buy order.
- Buy order can be manually adjusted.
- Deal recommendations consider buy order.

---

# Section 9 — Risk Profile Per Part

## Goal

Different PC parts have different risk levels when buying used.

DealWise should factor this into recommendations.

## Risk Levels

Low risk used:

- RAM
- Case
- Air cooler

Medium risk used:

- CPU
- Motherboard
- NVMe SSD

Higher risk used:

- GPU
- PSU
- AIO cooler

## Example

    This PSU is cheap, but used PSUs are higher risk.

    Recommendation:
    Avoid unless seller has proof, warranty, and strong history.

## Success Criteria

- Part type affects scam/risk scoring.
- High-risk parts require more evidence.
- Buy decision uses risk profile.

---

# Section 10 — Manual Item Checker

## Goal

The user should be able to paste a listing URL and get a full analysis.

This makes DealWise useful even if automatic marketplace search fails.

## User Flow

1. User opens Listing Checker.
2. User pastes a marketplace URL.
3. DealWise fetches or accepts listing details.
4. DealWise analyses the listing.
5. DealWise shows deal score, scam risk, build fit, budget fit, and recommended decision.
6. DealWise can generate a seller message.

## Example Output

    Authenticity Check

    Deal Score: 82/100
    Scam Risk: 3.4/10
    Build Fit: 91/100
    Budget Fit: 88/100
    Evidence Confidence: 54/100

    Decision: Negotiate

    Suggested offer: £215
    Max fair price: £240

    Ask these questions before buying:
    - Can you send a GPU-Z screenshot?
    - Can you send a photo with today's date?
    - Has it had any artifacting or overheating?

## Success Criteria

- User can paste URL.
- Listing checker does not require login.
- Listing checker can save result to local database.
- Seller message can be generated from checker result.

---

# Section 11 — Saved Part Lifecycle

## Goal

Saved listings should have realistic buying statuses.

## Statuses

- Found
- Watching
- Contacted Seller
- Waiting for Evidence
- Negotiating
- Bought
- Installed
- Returned
- Avoided
- Expired

## Success Criteria

- User can update listing status.
- Status is saved in database.
- Dashboard can summarise active buying workflow.

---

# Section 12 — Post-Purchase Tracking

## Goal

DealWise should continue helping after the user buys a part.

## Tracking Fields

- Bought price.
- Bought date.
- Seller.
- Marketplace.
- Warranty end date.
- Return window end date.
- Installed yes/no.
- Tested yes/no.
- Notes.
- Proof saved yes/no.

## Reminder Example

    Return window ends in 3 days.
    Test the GPU before then.

## Success Criteria

- Bought parts can be tracked.
- Return window can be recorded.
- Bought item affects budget and build progress.
- Future notification system can remind user.

---

# Section 13 — Confidence Scores

## Goal

Listing detail page should show multiple useful scores.

## Scores

- Deal Score: 0-100
- Scam Risk: 0-10
- Build Fit: 0-100
- Budget Fit: 0-100
- Evidence Confidence: 0-100
- Urgency Score: 0-100

## Example

    Deal Score: 87/100
    Scam Risk: 2.1/10
    Build Fit: 94/100
    Budget Fit: 88/100
    Evidence Confidence: 61/100
    Urgency Score: 72/100

    Final Decision: Negotiate

## Success Criteria

- Scores are visible but not overwhelming.
- Final decision is more important than raw numbers.
- Scores include reasoning.

---

# Section 14 — Current PC Import

## Goal

DealWise should import current PC information using inxi.

## Command

    inxi -Fx

## Detected Information

- System model.
- Motherboard.
- CPU.
- GPU.
- RAM.
- Storage.
- Kernel.
- Distro.
- Form factor notes if detectable.
- Upgrade limitations.

## Example Output

    Current PC:
    Dell Precision Tower 3420 SFF

    CPU:
    Intel i7-7700

    GPU:
    RX 6400 Low Profile

    RAM:
    16GB DDR4

    Storage:
    512GB NVMe

    Upgrade notes:
    SFF case limits GPU options.
    OEM motherboard limits platform upgrades.
    Full ATX rebuild may offer better value.

## Success Criteria

- User can import current PC.
- Results are saved locally.
- User can manually edit detected values.
- Upgrade warnings appear in PC Builder.

---

# Section 15 — Target Build Builder

## Goal

User should define the PC they are trying to build.

## Inputs

- Total budget.
- Use case.
- Target resolution.
- New/used preference.
- Platform preference.
- Current owned parts.
- Desired upgrade timeframe.

## Example

    Budget: £600
    Use case: 1440p gaming
    Preference: used GPU, new PSU
    Platform: AM5
    Target GPU: RX 6800 / RX 7700 XT
    Target CPU: Ryzen 5 7600 / Ryzen 7 7700

## Success Criteria

- User can create target build.
- Target build links to part checklist.
- Target build links to saved searches.
- Target build affects listing decisions.

---

# Section 16 — Parts Checklist

## Goal

Each part should be tracked as a checklist item.

## Part Categories

- CPU
- GPU
- Motherboard
- RAM
- Storage
- PSU
- Case
- Cooling
- Monitor
- Accessories

## Features

- Tick as needed.
- Tick as bought.
- Add budget.
- Add actual paid price.
- Add notes.
- Drag to reorder priority.
- Link saved searches.
- Link saved listings.
- Mark upgrade later.
- Mark avoid.

## Success Criteria

- User can track all parts.
- Checklist persists in database.
- Checklist affects budget and build progress.

---

# Section 17 — Marketplace Search Inside PC Builder

## Goal

Inside each part category, user should be able to search marketplaces.

## Controls

- Search bar.
- Saved searches.
- Marketplace toggles.
- New/used filters.
- Best deal filter.
- Discounted filter.
- Sort by price.
- Sort by deal score.
- Sort by scam risk.
- Sort by newest.
- Sort by seller rating if available.

## Listing Card Layout

Each listing card should show:

- Main image on the left.
- Item title.
- Price.
- Marketplace.
- Seller.
- Deal score.
- Scam score.
- Build fit.
- Budget fit.
- Recommendation.

## Buttons

- Open.
- Save.
- Compare.
- Check Scam.
- Generate Message.
- Mark Bought.

## Success Criteria

- Marketplace search can be filtered by part.
- Listings can be saved to target build.
- Listing card supports future images and scores.

---

# Section 18 — Recommended Phase 3 Implementation Split

Phase 3 should be built in smaller stages.

## Phase 3A — SQLite and Saved Listings

Deliverables:

- SQLite database.
- Database initialisation.
- Listing repository.
- Persistent live listings.
- Persistent saved listings.
- Durable deduplication.
- Manual save listing.
- Open listing URL.
- Listing status field.

## Phase 3B — PC Builder Foundation

Deliverables:

- PC Builder page.
- Current PC model.
- inxi -Fx import.
- Target build model.
- Budget model.
- Parts checklist.
- Bought/not bought status.
- Basic progress display.

## Phase 3C — Listing Intelligence Foundation

Deliverables:

- Listing detail view.
- Paste URL checker shell.
- Manual listing analysis form.
- Deal score placeholder.
- Scam score placeholder.
- Build fit placeholder.
- Budget fit placeholder.
- Buy decision placeholder.
- Evidence checklist by part type.
- Seller message generator.

## Phase 3D — UI Polish and Workflow

Deliverables:

- Expandable nested PC Builder UI.
- Indented subsections.
- Part category cards.
- Listing card improvements.
- Status labels.
- Empty states.
- Safer error handling.

---

# Phase 3 Non-Goals

Do not implement these yet:

- Marketplace login.
- Seller messaging automation.
- Buying automation.
- Payment handling.
- Cloud sync.
- AI API integration.
- Full compatibility database.
- Full reverse image automation.
- Full price prediction.

These can come later.

---

# Phase 3 Success Criteria

Phase 3 is successful when:

- Listings are stored persistently in SQLite.
- Duplicate listings are not repeatedly added.
- User can save listings.
- User can open saved listing URLs.
- User can create a target build.
- User can import current PC using inxi -Fx.
- User can track needed and bought parts.
- User can set a budget.
- User can paste a listing URL for manual checking.
- User can see a buy/negotiation/watch/wait/avoid decision placeholder.
- User can generate a seller message.
- App still launches cleanly.
- Phase 2 marketplace search still works.

---

# Suggested Commit Message

feat: plan Phase 3 PC builder and listing intelligence
