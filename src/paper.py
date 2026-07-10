from __future__ import annotations

from uuid import UUID  # noqa: TC003

from pydantic import AwareDatetime, BaseModel, Field
from workers import fetch as webfetch

TRACKER_API_BASE = "https://tnlkuelk67.execute-api.us-east-1.amazonaws.com/tracker"


class PaperNotFoundError(Exception): ...


class ReviewSummary(BaseModel):
    reviews_completed: int = Field(alias="ReviewsCompleted")
    review_invitations_accepted: int = Field(alias="ReviewInvitationsAccepted")
    review_invitations_sent: int = Field(alias="ReviewInvitationsSent")


class PaperInfo(BaseModel):
    uuid: UUID = Field(alias="Uuid")
    corresponding_author: str = Field(alias="CorrespondingAuthor")
    document_id: int = Field(alias="DocumentId")
    first_author: str = Field(alias="FirstAuthor")
    journal_acronym: str = Field(alias="JournalAcronym")
    journal_name: str = Field(alias="JournalName")
    last_updated: AwareDatetime = Field(alias="LastUpdated")
    latest_revision_number: int = Field(alias="LatestRevisionNumber")
    manuscript_title: str = Field(alias="ManuscriptTitle")
    pubd_number: str = Field(alias="PubdNumber")
    status: int = Field(alias="Status")
    submission_date: AwareDatetime = Field(alias="SubmissionDate")
    review_summary: ReviewSummary = Field(alias="ReviewSummary")


async def fetch_live_paper_info(manuscript_id: UUID | str) -> PaperInfo:
    manuscript_id = str(manuscript_id)
    response = await webfetch(f"{TRACKER_API_BASE}/{manuscript_id}")
    if response.status == 404:
        raise PaperNotFoundError(f"Paper with ID {manuscript_id} not found")
    if response.status != 200:
        raise Exception(f"Failed to fetch paper info: {response.status}")
    data = await response.json()
    return PaperInfo.model_validate(data)
