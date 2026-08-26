from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cv_template.models import CVTemplate


async def create(
    title: str, description: str | None, tex: str,tex_hash: str, db: AsyncSession
) -> CVTemplate:
    template = CVTemplate(
        title=title,
        description=description,
        tex=tex,
        tex_hash=tex_hash
    )

    db.add(template)

    await db.commit()

    await db.refresh(template)

    return template