# UI Update: Company Visibility and Portal Ordering

- Removed Accenture, HCLTech, and Wipro from the Companies sidebar UI as requested. This is a frontend visibility change; it does not delete database records or catalog definitions.
- Job portals are now sorted by current stored job count in descending order, with alphabetical order used to break ties.
- Remaining company entries are sorted by current stored job count in descending order, with alphabetical order used to break ties.
- Existing Select all controls and individual checkboxes remain in place.

After replacing the project files, restart Flask and hard-refresh the browser (Ctrl+F5) so the updated JavaScript is loaded.
