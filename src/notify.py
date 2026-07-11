import logging
import textwrap

import httpx2

from paper import PaperInfo

logger = logging.getLogger(__name__)


def send_ntfy_sh(topic: str, message: str):
    logger.debug(f"Sending notification to ntfy.sh topic '{topic}': {message}")
    try:
        with httpx2.Client() as client:
            response = client.post(
                f"https://ntfy.sh/{topic}",
                content=message,
                timeout=30,
            )
        if response.status_code >= 400:
            logger.warning(f"ntfy.sh returned HTTP {response.status_code}")
    except Exception:
        logger.exception("Failed to send notification")


def notify_paper_info_update(
    topic: str,
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
        send_ntfy_sh(
            topic,
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
        send_ntfy_sh(topic, text)
    elif paper_old is not None and paper_new is None:
        send_ntfy_sh(
            topic,
            f"Paper info deleted for {paper_old.manuscript_title}",
        )
    else:
        logger.debug("No changes in paper info, no notification sent.")
