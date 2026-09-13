import subprocess
import tempfile
from pathlib import Path


class LatexCompilationError(Exception):
    """Raised when the tex source fails to compile — a content problem, not a transient one."""


def render_tex_to_pdf(tex_source: str, timeout: int = 30) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tex_file = tmp_path / "template.tex"
        tex_file.write_text(tex_source, encoding="utf-8")

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-no-shell-escape",
            "-output-directory", str(tmp_path),
            str(tex_file),
        ]

        # First pass: proves the source compiles at all. Bail immediately on
        # failure rather than burning a second pass on broken input.
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise LatexCompilationError(
                f"pdflatex exceeded {timeout}s on first pass — likely pathological input."
            ) from exc

        if result.returncode != 0:
            raise LatexCompilationError(_tail(result))

        # Second pass: resolves \ref/\pageref/TOC now that .aux exists.
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise LatexCompilationError(
                f"pdflatex exceeded {timeout}s on second pass."
            ) from exc

        pdf_file = tmp_path / "template.pdf"
        if result.returncode != 0 or not pdf_file.exists():
            raise LatexCompilationError(_tail(result))

        return pdf_file.read_bytes()


def _tail(result: subprocess.CompletedProcess, max_chars: int = 3000) -> str:
    text = result.stdout or result.stderr or "pdflatex compilation failed with no output"
    return text[-max_chars:]