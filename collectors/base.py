
from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """
    Common interface for job-source collectors.

    Each collector must return a list of normalized job dictionaries.
    Collectors should use approved access methods and should not save
    records directly to the database.
    """

    source_name: str
    base_url: str
    source_type: str = "job_website"

    @abstractmethod
    def fetch_jobs(self) -> list[dict[str, Any]]:
        """
        Fetch and normalize job records.

        Each returned dictionary should contain:
            external_id: str | None
            url_hash: str
            title: str
            company: str | None
            location: str | None
            experience: str | None
            skills: str | None
            description: str | None
            job_url: str
            posted_at: str | None
            status: str

        Raises:
            RuntimeError: If the source cannot be accessed.
            ValueError: If the response format is invalid.
        """
        raise NotImplementedError
