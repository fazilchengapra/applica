"""Renders a template's raw .tex (containing \\VAR{}/\\BLOCK{} placeholders)
against a data payload, producing compile-ready LaTeX source.

Uses custom Jinja2 delimiters since {{ }} and {% %} collide with native
LaTeX syntax (curly braces are structurally significant in LaTeX).
"""
from jinja2 import Environment, BaseLoader, StrictUndefined, UndefinedError

_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\^{}",
}


def latex_escape(value) -> str:
    """Escape a plain-text value for safe insertion into LaTeX source.

    Never apply this to a value used as a command argument that isn't
    rendered text (e.g. a URL passed to \\href{}) — escaping a URL breaks it.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    # Backslash must be replaced first, or its replacement's own backslashes
    # get double-escaped by the subsequent iterations.
    result = value.replace("\\", _LATEX_ESCAPE_MAP["\\"])
    for char, replacement in _LATEX_ESCAPE_MAP.items():
        if char == "\\":
            continue
        result = result.replace(char, replacement)
    return result


class TexTemplateError(Exception):
    """Raised when the .tex source has a Jinja2 syntax error or references
    an undefined field — a content problem in the admin's template, not a
    transient failure."""


_env = Environment(
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    undefined=StrictUndefined,  # raises on any \VAR{typo_field} at render time
    loader=BaseLoader(),
)
_env.filters["latex_escape"] = latex_escape


def render_tex(tex_source: str, data: dict) -> str:
    try:
        template = _env.from_string(tex_source)
        return template.render(**data)
    except UndefinedError as exc:
        raise TexTemplateError(f"Template references an undefined field: {exc}") from exc
    except Exception as exc:
        raise TexTemplateError(f"Template syntax error: {exc}") from exc