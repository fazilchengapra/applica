"""Celery task: render a TailoredCV row with its selected CV template."""

import asyncio
import logging

from celery import shared_task
from sqlalchemy import select

from app.db.celery_db import get_celery_db_session
from app.modules.cv_render.service import render_pdf
from app.modules.cv_template.models import CVTemplate
from app.modules.cv_template.services.helpers.latex_render import LatexCompilationError
from app.modules.cv_template.services.helpers.s3_upload import upload_bytes
from app.modules.cv_template.services.helpers.tex_render import TexTemplateError
from app.modules.tailoring.models import CVRenderStatus, TailoredCV

logger = logging.getLogger(__name__)


async def _render(tailored_cv_id: str) -> None:
    async with get_celery_db_session() as session:
        result = await session.execute(
            select(TailoredCV).where(TailoredCV.id == tailored_cv_id)
        )
        tailored_cv = result.scalar_one_or_none()
        if tailored_cv is None:
            logger.warning("TailoredCV %s not found, skipping", tailored_cv_id)
            return

        if tailored_cv.cv_template_id is None:
            await _set_failed(
                session, tailored_cv, "No CV template selected for this tailored CV."
            )
            return

        template = await session.get(CVTemplate, tailored_cv.cv_template_id)
        if template is None or not template.is_active:
            await _set_failed(
                session, tailored_cv, "Selected CV template is not available."
            )
            return

        try:
            pdf_bytes = render_pdf(tailored_cv.cv_structure or {}, template.tex)
            file_key = upload_bytes(
                pdf_bytes, "tailored-cvs/pdf", "pdf", "application/pdf"
            )
        except (TexTemplateError, LatexCompilationError) as exc:
            # Template/content problem — permanent, not retryable.
            await _set_failed(session, tailored_cv, f"Template render failed: {exc}")
            return
        except Exception as exc:
            # S3/network — potentially transient, let Celery retry.
            logger.exception("Render failed for tailored_cv %s", tailored_cv_id)
            raise exc from exc

        tailored_cv.render_status = CVRenderStatus.completed
        tailored_cv.file_s3_key = file_key
        tailored_cv.render_error_message = None
        await session.commit()
        logger.info("Rendered tailored_cv %s -> %s", tailored_cv_id, file_key)


async def _set_failed(session, tailored_cv: TailoredCV, message: str) -> None:
    tailored_cv.render_status = CVRenderStatus.failed
    tailored_cv.render_error_message = message[:2000]
    await session.commit()


async def _mark_failed_after_retries(tailored_cv_id: str, message: str) -> None:
    async with get_celery_db_session() as session:
        result = await session.execute(
            select(TailoredCV).where(TailoredCV.id == tailored_cv_id)
        )
        tailored_cv = result.scalar_one_or_none()
        if tailored_cv is not None:
            await _set_failed(session, tailored_cv, message)


@shared_task(
    name="cv_render.render_tailored_cv",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def render_tailored_cv_task(self, tailored_cv_id: str) -> None:
    try:
        asyncio.run(_render(tailored_cv_id))
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed_after_retries(tailored_cv_id, str(exc)))
            return
        raise self.retry(exc=exc)