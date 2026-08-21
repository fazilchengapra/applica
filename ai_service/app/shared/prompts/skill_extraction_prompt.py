SKILLS_PROMPT = """Extract technical skills, tools, frameworks, and technologies mentioned in this job description or CV content.

Classify each skill as:
- "required": explicitly stated as required, must-have, mandatory, or a core responsibility
- "preferred": mentioned as nice-to-have, bonus, a plus, or preferred but not mandatory

Rules:
- Use canonical, commonly recognized names (e.g. "Node.js" not "nodejs", "PostgreSQL" not "postgres", "AWS" not "amazon web services")
- Only extract skills that are actually mentioned in the text below — do not infer or invent skills
- Do not extract soft skills (e.g. "communication", "teamwork") — only technical skills, tools, languages, frameworks, and platforms
- If a skill is mentioned multiple times, include it only once

Job description:
{description}"""