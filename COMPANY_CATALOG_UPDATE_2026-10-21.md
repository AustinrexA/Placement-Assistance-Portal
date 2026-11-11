# Company catalog update — 2026-10-21

## Visible company sources
- Infosys
- Amazon
- Deloitte
- HCLTech
- Cognizant
- Capgemini
- Tech Mahindra
- IBM

Wipro and Accenture have been removed from the active company career catalog. The UI endpoint builds its visible list from this catalog, so stale company career source rows are filtered out of the company sidebar without deleting job history or database records.

The five newly added companies use their official careers entry pages and the existing conservative JSON-LD `JobPosting` collector. Their presence in the UI is not a guarantee that the public page exposes structured vacancies; each source must be run and checked before describing its collector as verified. Infosys, Amazon and Deloitte existing collector paths remain unchanged.

## Commands
```powershell
python scripts/run_company_career_structured.py --source HCLTECH --max-results 100
python scripts/run_company_career_structured.py --source COGNIZANT --max-results 100
python scripts/run_company_career_structured.py --source CAPGEMINI --max-results 100
python scripts/run_company_career_structured.py --source TECHMAHINDRA --max-results 100
python scripts/run_company_career_structured.py --source IBM --max-results 100
```
