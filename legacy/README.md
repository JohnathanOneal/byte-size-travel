# Travel Newsletter RSS Aggregator

A simple RSS aggregator for travel blogs that will:
1. Collect articles from various travel blogs
2. Process them for content
3. Generate newsletters

## Configuration

Sources are managed in `config/sources.yaml`. Each source has:
- name: Blog name
- url: RSS feed URL
- category: Content category
- active: Whether to include this source
- last_checked: Timestamp of last successful check

## Project Status
Phase 0: Basic Content Ingestion (proof of concept)
Phase 1: Database / Config Overhaul
Phase 2: Content Enhancement / Classification
Phase 3: Newsletter Generation
