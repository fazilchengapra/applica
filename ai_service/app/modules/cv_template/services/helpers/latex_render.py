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

        # Run twice: first pass resolves references/TOC, second pass renders them correctly.
        for _ in range(2):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "-output-directory",
                    str(tmp_path),
                    str(tex_file),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        pdf_file = tmp_path / "template.pdf"
        if result.returncode != 0 or not pdf_file.exists():
            raise LatexCompilationError(
                result.stdout or result.stderr or "pdflatex compilation failed"
            )

        return pdf_file.read_bytes()
