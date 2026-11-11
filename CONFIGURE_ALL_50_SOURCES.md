

## Additional portal Actor candidates (configuration update v2)

The catalog now includes public Apify Store candidates for LinkedIn Jobs, Freshersworld, National Career Service (NCS), Jooble, QuikrJobs, and Jora. Their IDs and starter input objects are candidates only; they have not been live-tested in this project. Before each run, inspect the Actor's current Input and Pricing tabs. Keep `APIFY_ACCESS_APPROVED_<KEY>=false` until you confirm terms, pricing, and authorization. LinkedIn Jobs has no built-in default input schema in this runner; set `APIFY_INPUT_LINKEDIN_JOBS` to the exact JSON required by that Actor.

Actor candidates are community-maintained and can change, charge for results, or return output fields that need normalization. The batch runner should not be treated as proof that a portal is operational.


## Batch input-template fixes (Oct 2026)
- Added a built-in input template for the catalogued LinkedIn Actor.
- Changed Jora input to `keywords` (string), `location`, `country: in`, and `maxJobs`.
- Removed Hirist hard-coded city list; use the requested city or all locations for India-wide search.
- Normalize the `, India` suffix to city names for Actors that expect a city-only input.
- Lowered detail/page settings on selected test templates to limit requests.
- Approval flags remain false by default; this patch does not approve or run any Actor.
- Actor schemas can change; run small tests and check each Actor Input tab before live collection.
