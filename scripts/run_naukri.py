from collectors.normalization import normalize_job
from collectors.repository import save_jobs
from collectors.sources.naukri import NaukriAuthorizedFeedCollector

if __name__ == "__main__":
    collector = NaukriAuthorizedFeedCollector()
    try:
        raw_jobs = collector.fetch_jobs()
        normalized = []
        for raw in raw_jobs:
            try:
                normalized.append(normalize_job(raw))
            except (ValueError, TypeError) as exc:
                print(f"Skipping invalid listing: {exc}")

        result = save_jobs(
            source_name=collector.source_name,
            base_url=collector.base_url,
            jobs=normalized,
            source_type=collector.source_type,
        )
        print(result)
    except Exception as exc:
        print(f"Naukri collection did not run: {exc}")
        raise SystemExit(1)
