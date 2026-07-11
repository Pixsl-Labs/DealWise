# DealWise RAM Hunt Phase

## Purpose

Urgent RAM hunting workflow for the AM5 build.

## Current target

- CPU: Ryzen 7 7800X3D
- Motherboard: ASUS TUF Gaming B850-E WiFi
- Final RAM: 32GB 2x16GB desktop DDR5-6000, ideally CL30 AMD EXPO
- Temporary RAM: cheap desktop DDR5 stick for POST/testing only

## Implemented

- RAM Hunt page.
- RAM profile controls.
- RAM-specific query generator.
- Vinted batch search creation.
- Browser handoff URLs for eBay, Gumtree, CeX, Facebook Marketplace and retail references.
- RAM parser and score service.
- RAM seller message generator.
- PC Builder RAM integration.
- Unit tests for RAM parsing and scoring basics.

## Facebook Marketplace

Facebook Marketplace is browser handoff/manual import only.

DealWise does not store Facebook credentials, does not automate login, and does not browser-scrape Facebook.
