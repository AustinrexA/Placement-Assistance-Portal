import csv
from collectors.normalization import normalize_job
from collectors.repository import save_jobs


def import_csv(path: str):
    normalized = []
    skipped = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"title", "job_url"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must include at least these headers: title, job_url")

        for row_number, row in enumerate(reader, start=2):
            try:
                normalized.append(normalize_job(row))
            except (ValueError, TypeError) as exc:
                skipped += 1
                print(f"Skipping CSV row {row_number}: {exc}")

    result = save_jobs(
        source_name="CSV Import",
        base_url="https://example.invalid/",
        jobs=normalized,
        source_type="authorized_import",
    )
    result["skipped"] = skipped
    return result
