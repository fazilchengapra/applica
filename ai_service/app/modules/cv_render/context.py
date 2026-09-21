"""Canonical render context for tailored CVs.

This is the single contract between the structured CV the writer produces
(CVContent / tailored_cvs.cv_structure) and the LaTeX templates. Every
\\VAR{...} a template may use is derived here, deterministically.

Keep this file the source of truth: template validation (SAMPLE_CV_DATA) and
user rendering both go through build_render_context, so a template validated at
upload time is guaranteed to render real data with the same field names.
"""

from typing import Any


def _join(values: list[str]) -> str:
    return ", ".join(str(v) for v in values if v)


def _date_range(entry: dict) -> str:
    start = entry.get("start_date")
    end = entry.get("end_date")
    if entry.get("is_current"):
        end = end or "Present"
    if start and end:
        return f"{start} -- {end}"
    return start or end or ""


def _experience_entry(entry: dict) -> dict:
    technologies = entry.get("technologies") or []
    return {
        "title": entry.get("title") or "",
        "company": entry.get("company") or "",
        "location": entry.get("location") or "",
        "start_date": entry.get("start_date") or "",
        "end_date": entry.get("end_date") or "",
        "dates": _date_range(entry),
        "is_current": bool(entry.get("is_current")),
        "bullets": entry.get("bullets") or [],
        "technologies": technologies,
        "technologies_list": _join(technologies),
    }


def _project_entry(entry: dict) -> dict:
    technologies = entry.get("technologies") or []
    return {
        "name": entry.get("name") or "",
        "url": entry.get("url") or "",
        "date": entry.get("date") or "",
        "bullets": entry.get("bullets") or [],
        "technologies": technologies,
        "technologies_list": _join(technologies),
    }


def _education_note(entry: dict) -> str:
    parts: list[str] = []
    if entry.get("field_of_study"):
        parts.append(str(entry["field_of_study"]))
    dates = _date_range(entry)
    if dates:
        parts.append(dates)
    if entry.get("gpa"):
        parts.append(f"GPA: {entry['gpa']}")
    return "; ".join(parts)


def _education_entry(entry: dict) -> dict:
    return {
        "institution": entry.get("institution") or "",
        "degree": entry.get("degree") or "",
        "field_of_study": entry.get("field_of_study") or "",
        "start_date": entry.get("start_date") or "",
        "end_date": entry.get("end_date") or "",
        "gpa": entry.get("gpa") or "",
        "dates": _date_range(entry),
        "note": _education_note(entry),
    }


def build_render_context(cv_content: dict) -> dict:
    """Map a persisted CVContent dict into the template-facing render context."""
    contact = cv_content.get("contact") or {}
    experience = [
        _experience_entry(entry)
        for entry in (cv_content.get("experience") or [])
    ]
    education = [
        _education_entry(entry)
        for entry in (cv_content.get("education") or [])
    ]
    skills = [str(skill) for skill in (cv_content.get("skills") or [])]
    certifications = [
        str(item) for item in (cv_content.get("certifications") or [])
    ]
    full_name = contact.get("full_name") or ""

    contact_scalar = {
        "email": contact.get("email") or "",
        "phone": contact.get("phone") or "",
        "location": contact.get("location") or "",
        "linkedin": contact.get("linkedin") or "",
        "github": contact.get("github") or "",
        "portfolio": contact.get("portfolio") or "",
    }

    return {
        "full_name": full_name,
        "name": full_name,
        "email": contact_scalar["email"],
        "phone": contact_scalar["phone"],
        "location": contact_scalar["location"],
        "linkedin": contact_scalar["linkedin"],
        "github": contact_scalar["github"],
        "portfolio": contact_scalar["portfolio"],
        "contact": dict(contact_scalar),
        "title": experience[0]["title"] if experience else "",
        "tagline": _join(skills[:6]),
        "summary": cv_content.get("summary") or "",
        "skills": skills,
        "skills_list": _join(skills),
        "skill_categories": (
            [{"label": "Skills", "items": _join(skills)}] if skills else []
        ),
        "experience": experience,
        "projects": [
            _project_entry(entry) for entry in (cv_content.get("projects") or [])
        ],
        "education": education,
        "certifications": certifications,
        "certifications_list": _join(certifications),
    }


SAMPLE_CV_CONTENT: dict = {
    "contact": {
        "full_name": "Jordan Alvarez",
        "email": "jordan.alvarez@example.com",
        "phone": "555-0134",
        "location": "Austin, TX",
        "linkedin": "https://linkedin.com/in/jalvarez",
        "github": "https://github.com/jalvarez",
        "portfolio": None,
    },
    "summary": (
        "Full-Stack Developer with production experience building scalable, "
        "real-time web applications using modern frameworks."
    ),
    "experience": [
        {
            "title": "Full-Stack Developer",
            "company": "Acme Corp",
            "location": "Austin, TX",
            "start_date": "Jan 2024",
            "end_date": None,
            "is_current": True,
            "bullets": [
                "Built scalable, responsive web interfaces using React.js and TypeScript",
                "Developed and integrated RESTful APIs for core business workflows",
                "Improved application performance using Redis caching and Docker",
            ],
            "evidence_item_ids": ["sample-exp-1"],
            "technologies": ["React.js", "TypeScript", "Redis", "Docker"],
        }
    ],
    "projects": [],
    "education": [
        {
            "institution": "State University",
            "degree": "B.Sc. Computer Science",
            "field_of_study": "Computer Science",
            "start_date": None,
            "end_date": "2023",
            "gpa": None,
        }
    ],
    "skills": [
        "Node.js",
        "Express.js",
        "React.js",
        "Python",
        "Django",
        "REST API Design",
        "MongoDB",
        "PostgreSQL",
        "AWS EC2",
        "Docker",
        "Git",
    ],
    "certifications": ["AWS Certified Developer -- Associate"],
}