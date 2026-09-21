"""Fixed sample payload used to validate every template at upload time.

Built from SAMPLE_CV_CONTENT through build_render_context so the fields a
template exercises at validation time are exactly the fields a real tailored CV
(cv_structure -> build_render_context) will render with at production time.
"""

from app.modules.cv_render.context import SAMPLE_CV_CONTENT, build_render_context

SAMPLE_CV_DATA: dict = build_render_context(SAMPLE_CV_CONTENT)