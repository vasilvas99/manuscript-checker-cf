import logging
import sys
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings

from db import connect_db, delete_stored_paper, get_stored_paper, upsert_stored_paper
from notify import notify_paper_info_update
from paper import PaperNotFoundError, fetch_live_paper_info

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    MANUSCRIPT_ID: str = "18003827-1245-452b-b4a5-e2afc2fa8676"
    NTFY_TOPIC_PREFIX: str = "paper-info-updates"
    MANUSCRIPT_CHECKER_DB: Path = PROJECT_ROOT / "manuscript_checker.sqlite3"
    LOG_LEVEL: str = "INFO"

    @computed_field
    @property
    def notify_topic(self) -> str:
        return f"{self.NTFY_TOPIC_PREFIX}-{self.MANUSCRIPT_ID}"


SETTINGS = Settings()


def run_once() -> int:
    with connect_db(SETTINGS.MANUSCRIPT_CHECKER_DB) as db:
        paper = get_stored_paper(db, SETTINGS.MANUSCRIPT_ID)
        try:
            paper_live = fetch_live_paper_info(SETTINGS.MANUSCRIPT_ID)
        except PaperNotFoundError:
            logger.warning(f"Paper with ID {SETTINGS.MANUSCRIPT_ID} not found")
            notify_paper_info_update(SETTINGS.notify_topic, paper, None)
            delete_stored_paper(db, SETTINGS.MANUSCRIPT_ID)
            return 0
        except Exception:
            logger.exception("Failed to fetch live paper info")
            return 1

        notify_paper_info_update(SETTINGS.notify_topic, paper, paper_live)

        if paper != paper_live:
            upsert_stored_paper(db, paper_live)
            logger.info(f"Paper info updated for {SETTINGS.MANUSCRIPT_ID}")
        else:
            logger.info(f"Paper info unchanged for {SETTINGS.MANUSCRIPT_ID}")

    return 0


def main() -> int:
    logging.basicConfig(
        level=SETTINGS.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return run_once()


if __name__ == "__main__":
    sys.exit(main())
