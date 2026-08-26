import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cv_template.models import CVTemplate
from app.modules.cv_template.services.helpers.latex_render import LatexCompilationError, render_tex_to_pdf
from app.modules.cv_template.services.helpers.pdf_snapshot import render_first_page_png
from app.modules.cv_template.services.helpers.s3_upload import upload_bytes

logger = logging.getLogger(__name__)


async def process_cv_template(template_id: str, session: AsyncSession) -> None:
    template = await session.get(CVTemplate, template_id)
    if template is None:
        logger.warning("cv_template %s not found, skipping", template_id)
        return

    try:
        pdf_bytes = render_tex_to_pdf(template.tex)
    except LatexCompilationError:
        # Deterministic content error — retrying won't help, so we don't re-raise.
        logger.exception("LaTeX compilation failed for template %s", template_id)
        await session.rollback()
        return

    image_bytes = render_first_page_png(pdf_bytes)

    file_key = upload_bytes(pdf_bytes, "cv-templates/pdf", "pdf", "application/pdf")
    image_key = upload_bytes(image_bytes, "cv-templates/thumbnail", "png", "image/png")

    template.file_s3_key = file_key
    template.image_s3_key = image_key
    template.is_active = True

    await session.commit()