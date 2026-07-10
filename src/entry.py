import logging
import textwrap

from workers import Response, WorkerEntrypoint, fetch

from db import delete_stored_paper, get_stored_paper, upsert_stored_paper
from paper import PaperInfo, PaperNotFoundError, fetch_live_paper_info

logger = logging.getLogger(__name__)

MANUSCRIPT_ID = "18003827-1245-452b-b4a5-e2afc2fa8676"
NOTIFY_TOPIC = f"paper-info-updates-{MANUSCRIPT_ID}"


async def send_ntfy_sh(topic: str, message: str):
    logger.debug(f"Sending notification to ntfy.sh topic '{topic}': {message}")
    try:
        await fetch(
            f"https://ntfy.sh/{topic}",
            method="POST",
            body=message.encode("utf-8"),
        )
    except Exception as e:
        logger.exception("Failed to send notification", exc_info=e)


async def notify_paper_info_update(
    paper_old: PaperInfo | None,
    paper_new: PaperInfo | None,
):
    template = textwrap.dedent(
        """\
        Paper info updated for manuscript {title}:
            Revision Number: {old_revision} -> {new_revision}
            Completed Reviews: {old_completed} -> {new_completed}
            Review Invitations Accepted: {old_accepted} -> {new_accepted}
            Review Invitations Sent: {old_sent} -> {new_sent}"""
    )

    if paper_old is None and paper_new is not None:
        await send_ntfy_sh(
            NOTIFY_TOPIC,
            f"New paper info stored for {paper_new.manuscript_title}",
        )
    elif paper_old is not None and paper_new is not None and paper_old != paper_new:
        text = template.format(
            title=paper_new.manuscript_title,
            old_revision=paper_old.latest_revision_number,
            new_revision=paper_new.latest_revision_number,
            old_completed=paper_old.review_summary.reviews_completed,
            new_completed=paper_new.review_summary.reviews_completed,
            old_accepted=paper_old.review_summary.review_invitations_accepted,
            new_accepted=paper_new.review_summary.review_invitations_accepted,
            old_sent=paper_old.review_summary.review_invitations_sent,
            new_sent=paper_new.review_summary.review_invitations_sent,
        )
        await send_ntfy_sh(NOTIFY_TOPIC, text)
    elif paper_old is not None and paper_new is None:
        await send_ntfy_sh(
            NOTIFY_TOPIC,
            f"Paper info deleted for {paper_old.manuscript_title}",
        )
    else:
        logger.debug("No changes in paper info, no notification sent.")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        paper = await get_stored_paper(self.env.DB, MANUSCRIPT_ID)
        
        if paper is None:
            return Response(
                f"No stored paper info for manuscript ID {MANUSCRIPT_ID}",
                status=404,
                headers={"Content-Type": "text/plain"},
            )
            
        return Response(
            paper.model_dump_json(),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    async def scheduled(self, *args, **kwargs):
        paper = await get_stored_paper(self.env.DB, MANUSCRIPT_ID)
        try:
            paper_live = await fetch_live_paper_info(MANUSCRIPT_ID)
        except PaperNotFoundError:
            logger.warning(f"Paper with ID {MANUSCRIPT_ID} not found")
            await delete_stored_paper(self.env.DB, MANUSCRIPT_ID)
            return
        except Exception as e:
            logger.exception("Failed to fetch live paper info", exc_info=e)
            return

        await notify_paper_info_update(paper, paper_live)

        if paper != paper_live:
            await upsert_stored_paper(self.env.DB, paper_live)
            logger.info(f"Paper info updated for {MANUSCRIPT_ID}")
        else:
            logger.info(f"Paper info unchanged for {MANUSCRIPT_ID}")
