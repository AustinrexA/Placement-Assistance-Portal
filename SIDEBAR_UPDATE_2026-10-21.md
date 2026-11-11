# Sidebar update — 2026-10-21

- Restored the expandable Companies sidebar group with an aligned master checkbox and plus/minus indicator.
- Displayed Infosys as the first company integration; additional companies stay hidden until individually verified and rolled out.
- Applied distinct navigation glyphs for Dashboard, Job Portal, Companies, and Reports.
- Increased sidebar contrast on hover/focus and standardized icon, checkbox, label, count, and dropdown alignment.
- Added cache-busting versions to the CSS and JavaScript assets.

Validation: Python compilation and `node --check static/app.js` passed. Full pytest collection could not run in this environment because Flask is not installed (`ModuleNotFoundError: flask`). No database writes or deployment were performed.
