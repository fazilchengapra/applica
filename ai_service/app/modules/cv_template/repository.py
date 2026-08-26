from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.cv_template.models import CVTemplate
from app.modules.cv_template.schemas import CVTemplateAdminOut


async def create(
    title: str, description: str | None, tex: str, tex_hash: str, db: AsyncSession
) -> CVTemplate:
    template = CVTemplate(
        title=title, description=description, tex=tex, tex_hash=tex_hash
    )

    db.add(template)

    await db.commit()

    await db.refresh(template)

    return template


async def get_all(
    db: AsyncSession,
    *,
    include_inactive: bool = True,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[CVTemplateAdminOut]:
    stmt = select(CVTemplate)

    if not include_inactive:
        stmt = stmt.where(CVTemplate.is_active.is_(True))

    if not include_deleted:
        stmt = stmt.where(CVTemplate.deleted_at.is_(None))

    stmt = stmt.order_by(CVTemplate.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    templates = result.scalars().all()

    return [CVTemplateAdminOut.model_validate(template) for template in templates]


async def get_by_id(
    db: AsyncSession,
    template_id: UUID,
    *,
    include_inactive: bool = False,
    include_deleted: bool = False,
) -> CVTemplate | None:
    stmt = select(CVTemplate).where(CVTemplate.id == template_id)
    if not include_deleted:
        stmt = stmt.where(CVTemplate.deleted_at.is_(None))
    if not include_inactive:
        stmt = stmt.where(CVTemplate.is_active.is_(True))
    return await db.scalar(stmt)


async def soft_delete(db: AsyncSession, template_id: UUID) -> CVTemplate | None:
    template = await db.scalar(
        select(CVTemplate).where(
            CVTemplate.id == template_id, CVTemplate.deleted_at.is_(None)
        )
    )
    if template is None:
        return None

    template.deleted_at = datetime.now(timezone.utc)
    template.is_active = False
    await db.commit()
    await db.refresh(template)
    return template
