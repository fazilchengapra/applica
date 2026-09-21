"""Rendering of tailored CVs to PDF via LaTeX CV templates."""

from app.modules.cv_render.context import SAMPLE_CV_CONTENT, build_render_context   

__all__ = ["build_render_context", "SAMPLE_CV_CONTENT"]