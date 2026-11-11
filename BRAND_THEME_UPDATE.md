# V4Career Brand Theme Update

## Palette
- Brand orange: `#FF6700`
- Warm white page background: `#FFF9F3`
- White cards: `#FFFFFF`
- Deep slate navigation: `#263445`
- Pale orange selected surfaces: `#FFE8D8`
- Warm border: `#EADFD5`

## Scope
- Applied orange accents to active sidebar navigation, interactive controls, report-card highlights, focus rings, and export/search actions.
- Applied warm-white page background and warmer card/table/filter surfaces.
- Kept the dark slate sidebar for contrast and readability.
- Updated login page background, input focus, and submit button to match.
- Preserved application logic, collectors, database access code, and existing feature behavior.

## Verification
- Python compilation: passed.
- JavaScript syntax check: passed.
- Full pytest suite could not collect `tests/test_api.py` in this packaging environment because Flask is not installed. Run `python -m pip install -r requirements.txt` and `python -m pytest -q` in the project's virtual environment.
- No live scraping, database writes, or deployment performed.
