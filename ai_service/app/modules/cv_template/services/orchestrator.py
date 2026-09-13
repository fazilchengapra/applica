import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cv_template.models import CVTemplate, CVTemplateStatus
from app.modules.cv_template.services.helpers.latex_render import (
    LatexCompilationError,
    render_tex_to_pdf,
)
from app.modules.cv_template.services.helpers.pdf_snapshot import render_first_page_png
from app.modules.cv_template.services.helpers.s3_upload import upload_bytes
from app.modules.cv_template.services.helpers.sample_data import SAMPLE_CV_DATA
from app.modules.cv_template.services.helpers.tex_render import TexTemplateError, render_tex

logger = logging.getLogger(__name__)


async def process_cv_template(template_id: str, session: AsyncSession) -> None:
    template = await session.get(CVTemplate, template_id)
    if template is None:
        logger.warning("cv_template %s not found, skipping", template_id)
        return

    try:
        rendered_tex = render_tex(template.tex, SAMPLE_CV_DATA)
    except TexTemplateError as exc:
        logger.warning("Template %s failed Jinja render: %s", template_id, exc)
        await _mark_failed(session, template, str(exc))
        return

    try:
        pdf_bytes = render_tex_to_pdf(rendered_tex)
    except LatexCompilationError as exc:
        logger.warning("Template %s failed pdflatex compile: %s", template_id, exc)
        await _mark_failed(session, template, str(exc))
        return

    try:
        image_bytes = render_first_page_png(pdf_bytes)
        file_key = upload_bytes(pdf_bytes, "cv-templates/pdf", "pdf", "application/pdf")
        image_key = upload_bytes(image_bytes, "cv-templates/thumbnail", "png", "image/png")
    except Exception as exc:
        # Thumbnail/S3 issues ARE potentially transient (network, S3
        # throttling) — re-raise so Celery's retry kicks in, rather than
        # marking the template permanently failed.
        logger.exception("Post-compile processing failed for template %s", template_id)
        raise

    template.file_s3_key = file_key
    template.image_s3_key = image_key
    template.status = CVTemplateStatus.active
    template.is_active = True
    template.error_message = None
    await session.commit()
    logger.info("Template %s processed successfully", template_id)


async def _mark_failed(session: AsyncSession, template: CVTemplate, error_message: str) -> None:
    template.status = CVTemplateStatus.failed
    template.is_active = False
    template.error_message = error_message[:2000]
    await session.commit()