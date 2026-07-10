import logging
from uuid import UUID

from paper import PaperInfo

logger = logging.getLogger(__name__)


async def get_stored_paper(db, uuid: UUID | str) -> PaperInfo | None:
    row = (
        await db.prepare(
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
        """
        )
        .bind(str(uuid))
        .first()
    )

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


async def upsert_stored_paper(db, paper: PaperInfo) -> PaperInfo:
    data = paper.model_dump(by_alias=True, mode="json")
    review_summary = data["ReviewSummary"]

    await (
        db.prepare(
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
            review_summary_reviews_completed = excluded.review_summary_reviews_completed,  -- noqa
            review_summary_review_invitations_accepted = excluded.review_summary_review_invitations_accepted,  -- noqa
            review_summary_review_invitations_sent = excluded.review_summary_review_invitations_sent  -- noqa
        """  # noqa: E501
        )
        .bind(
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
        )
        .run()
    )

    saved_paper = await get_stored_paper(db, data["Uuid"])

    if saved_paper is None:
        raise RuntimeError(f"Failed to upsert paper with UUID {data['Uuid']}")

    return saved_paper


async def delete_stored_paper(db, uuid: UUID | str) -> None:
    await db.prepare("DELETE FROM paper_info WHERE uuid = ?").bind(str(uuid)).run()
