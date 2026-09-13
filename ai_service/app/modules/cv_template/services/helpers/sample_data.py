"""Fixed sample payload used to validate every template at upload time.

This is the canonical schema every admin-uploaded .tex must target. If a
template needs a field not present here, extend this dict (and document the
new field for admins) rather than inventing a one-off shape per template.
"""

SAMPLE_CV_DATA: dict = {
    "name": "Jordan Alvarez",
    "title": "Full-Stack Developer",
    "tagline": "Node.js, Express.js, React.js, Python/Django",
    "contact": {
        "email": "jordan.alvarez@example.com",
        "phone": "555-0134",
        "location": "Austin, TX",
        "github": "https://github.com/jalvarez",
        "linkedin": "https://linkedin.com/in/jalvarez",
    },
    "summary": (
        "Full-Stack Developer with production experience building scalable, "
        "real-time web applications using modern frameworks."
    ),
    "skill_categories": [
        {"label": "Backend", "items": "Node.js, Express.js, Python, Django, REST API Design"},
        {"label": "Frontend", "items": "React.js, Next.js, TypeScript, Tailwind CSS"},
        {"label": "Database", "items": "MongoDB, PostgreSQL, AWS RDS"},
        {"label": "Cloud & DevOps", "items": "AWS EC2, Docker, Nginx, Git"},
    ],
    "experience": [
        {
            "title": "Full-Stack Developer",
            "company": "Acme Corp, Remote",
            "dates": "Jan 2024 -- Present",
            "bullets": [
                "Built scalable, responsive web interfaces using React.js and TypeScript",
                "Developed and integrated RESTful APIs for core business workflows",
                "Improved application performance using Redis caching and Docker",
            ],
        },
    ],
    "education": [
        {"degree": "B.Sc. Computer Science", "institution": "State University", "note": "Graduated 2023"},
    ],
}