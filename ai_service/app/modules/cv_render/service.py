"""Render a tailored CV's structured content into PDF bytes via a LaTeX template."""

from app.modules.cv_render.context import build_render_context
from app.modules.cv_template.services.helpers.latex_render import render_tex_to_pdf
from app.modules.cv_template.services.helpers.tex_render import render_tex


def render_pdf(cv_content: dict, tex_source: str) -> bytes:
    """Render cv_structure (CVContent dict) through a template's .tex to a PDF."""
    rendered_tex = render_tex(tex_source, build_render_context(cv_content))
    return render_tex_to_pdf(rendered_tex)