import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from paper import PaperInfo

logger = logging.getLogger(__name__)


@contextmanager
def connect_db(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        initialize_db(db)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_db(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_info (
            uuid TEXT PRIMARY KEY,
            corresponding_author TEXT NOT NULL,
            document_id INTEGER NOT NULL,
            first_author TEXT NOT NULL,
            journal_acronym TEXT NOT NULL,
            journal_name TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            latest_revision_number INTEGER NOT NULL,
            manuscript_title TEXT NOT NULL,
            pubd_number TEXT NOT NULL,
            status INTEGER NOT NULL,
            submission_date TEXT NOT NULL,
            review_summary_reviews_completed INTEGER NOT NULL,
            review_summary_review_invitations_accepted INTEGER NOT NULL,
            review_summary_review_invitations_sent INTEGER NOT NULL
        )
        """
    )
    db.commit()


def get_stored_paper(db: sqlite3.Connection, uuid: UUID | str) -> PaperInfo | None:
    row = db.execute(
        """
        SELECT
            uuid,
            corresponding_author,
            document_id,
            first_author,
            journal_acronym,
            journal_name,
            last_updated,
            latest_revision_number,
            manuscript_title,
            pubd_number,
            status,
            submission_date,
            review_summary_reviews_completed,
            review_summary_review_invitations_accepted,
            review_summary_review_invitations_sent
        FROM paper_info
        WHERE uuid = ?
        LIMIT 1
        """,
        (str(uuid),),
    ).fetchone()

    if row is None:
        return None

    return PaperInfo.model_validate(
        {
            "Uuid": row["uuid"],
            "CorrespondingAuthor": row["corresponding_author"],
            "DocumentId": row["document_id"],
            "FirstAuthor": row["first_author"],
            "JournalAcronym": row["journal_acronym"],
            "JournalName": row["journal_name"],
            "LastUpdated": row["last_updated"],
            "LatestRevisionNumber": row["latest_revision_number"],
            "ManuscriptTitle": row["manuscript_title"],
            "PubdNumber": row["pubd_number"],
            "Status": row["status"],
            "SubmissionDate": row["submission_date"],
            "ReviewSummary": {
                "ReviewsCompleted": row["review_summary_reviews_completed"],
                "ReviewInvitationsAccepted": row[
                    "review_summary_review_invitations_accepted"
                ],
                "ReviewInvitationsSent": row["review_summary_review_invitations_sent"],
            },
        }
    )


def upsert_stored_paper(db: sqlite3.Connection, paper: PaperInfo) -> PaperInfo:
    data = paper.model_dump(by_alias=True, mode="json")
    review_summary = data["ReviewSummary"]

    db.execute(
        """
        INSERT INTO paper_info (
            uuid,
            corresponding_author,
            document_id,
            first_author,
            journal_acronym,
            journal_name,
            last_updated,
            latest_revision_number,
            manuscript_title,
            pubd_number,
            status,
            submission_date,
            review_summary_reviews_completed,
            review_summary_review_invitations_accepted,
            review_summary_review_invitations_sent
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(uuid) DO UPDATE SET
            corresponding_author = excluded.corresponding_author,
            document_id = excluded.document_id,
            first_author = excluded.first_author,
            journal_acronym = excluded.journal_acronym,
            journal_name = excluded.journal_name,
            last_updated = excluded.last_updated,
            latest_revision_number = excluded.latest_revision_number,
            manuscript_title = excluded.manuscript_title,
            pubd_number = excluded.pubd_number,
            status = excluded.status,
            submission_date = excluded.submission_date,
            review_summary_reviews_completed = excluded.review_summary_reviews_completed,
            review_summary_review_invitations_accepted = excluded.review_summary_review_invitations_accepted,
            review_summary_review_invitations_sent = excluded.review_summary_review_invitations_sent
        """, #noqa E501
        (
            data["Uuid"],
            data["CorrespondingAuthor"],
            data["DocumentId"],
            data["FirstAuthor"],
            data["JournalAcronym"],
            data["JournalName"],
            data["LastUpdated"],
            data["LatestRevisionNumber"],
            data["ManuscriptTitle"],
            data["PubdNumber"],
            data["Status"],
            data["SubmissionDate"],
            review_summary["ReviewsCompleted"],
            review_summary["ReviewInvitationsAccepted"],
            review_summary["ReviewInvitationsSent"],
        ),
    )
    db.commit()

    saved_paper = get_stored_paper(db, data["Uuid"])

    if saved_paper is None:
        raise RuntimeError(f"Failed to upsert paper with UUID {data['Uuid']}")

    return saved_paper


def delete_stored_paper(db: sqlite3.Connection, uuid: UUID | str) -> None:
    db.execute("DELETE FROM paper_info WHERE uuid = ?", (str(uuid),))
    db.commit()
