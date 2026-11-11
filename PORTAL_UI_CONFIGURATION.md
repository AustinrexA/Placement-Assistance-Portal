# V4Career portal/company UI configuration

## Changes in this package
- Portal API now exposes only portal sources whose Actor/feed, input configuration, API token, and explicit approval flag are configured at runtime.
- Company Career API/UI now exposes only company sources with a validated collector (`verified_collector`) or a fully configured and approved company Actor.
- Reports use the same portal list returned by the API instead of a separate hard-coded list.
- Expanded common field aliases in `scripts/run_source_apify.py` to improve job field mapping.

## Important
- This does not claim all 25 portals are operational. The 25-name catalog is retained for configuration and script discovery, but entries without reviewed Actor IDs/input schemas and explicit approval are hidden from the UI.
- The project `.env` is intentionally not packaged. Copy your existing local `.env` into the extracted `V4Career` folder and do not share it. Existing database settings and credentials must be preserved.
- The 5 missing Actor IDs remain unresolved; do not use guessed IDs. Portal API visibility is determined from the actual runtime `.env` values.
- Companies shown in the UI are limited to validated collector entries or explicitly configured company Actors. This filter does not delete existing database jobs or source rows.
