"""Ownership-scoped queries for ATS reports and the role vocabulary cache."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ats.models import ATSReport, RoleVocabulary


async def find_current_cv_version(db: AsyncSession, user_id: int):
    from app.modules.master_cv.models.master_cv import CVStatus, MasterCV, MasterCVVersion

    master_cv = await db.scalar(select(MasterCV).where(MasterCV.user_id == user_id))
    if master_cv is None:
        return None, "not_found"

    version = await db.scalar(
        select(MasterCVVersion).where(
            MasterCVVersion.master_cv_id == master_cv.id,
            MasterCVVersion.is_current.is_(True),
        )
    )
    if version is None:
        return None, "not_found"
    if version.status != CVStatus.COMPLETED:
        return None, "not_ready"
    return version, None


async def find_owned_cv_version(
    db: AsyncSession, user_id: int, cv_version_id: UUID
):
    """A specific version, proven to belong to the caller. ``(version, error)``."""
    from app.modules.master_cv.models.master_cv import CVStatus, MasterCV, MasterCVVersion

    version = await db.scalar(
        select(MasterCVVersion)
        .join(MasterCV, MasterCV.id == MasterCVVersion.master_cv_id)
        .where(MasterCVVersion.id == cv_version_id, MasterCV.user_id == user_id)
    )
    if version is None:
        return None, "not_found"
    if version.status != CVStatus.COMPLETED:
        return None, "not_ready"
    return version, None


async def get_report(
    db: AsyncSession,
    cv_version_id: UUID,
    content_hash: str,
    ruleset_version: int,
) -> ATSReport | None:
    return await db.scalar(
        select(ATSReport).where(
            ATSReport.cv_version_id == cv_version_id,
            ATSReport.content_hash == content_hash,
            ATSReport.ruleset_version == ruleset_version,
        )
    )


async def delete_report(
    db: AsyncSession, cv_version_id: UUID, content_hash: str, ruleset_version: int
) -> None:
    await db.execute(
        delete(ATSReport).where(
            ATSReport.cv_version_id == cv_version_id,
            ATSReport.content_hash == content_hash,
            ATSReport.ruleset_version == ruleset_version,
        )
    )


async def list_reports(
    db: AsyncSession, user_id: int, cv_version_id: UUID | None, limit: int, offset: int
) -> tuple[int, list[ATSReport]]:
    stmt = select(ATSReport).where(ATSReport.user_id == user_id)
    if cv_version_id is not None:
        stmt = stmt.where(ATSReport.cv_version_id == cv_version_id)

    total = await db.scalar(
        select(func.count()).select_from(stmt.subquery())
    )
    rows = await db.execute(
        stmt.order_by(ATSReport.created_at.desc()).limit(limit).offset(offset)
    )
    return int(total or 0), list(rows.scalars())


async def get_report_owned(
    db: AsyncSession, report_id: UUID, user_id: int
) -> ATSReport | None:
    return await db.scalar(
        select(ATSReport).where(ATSReport.id == report_id, ATSReport.user_id == user_id)
    )


async def get_role_vocabulary(db: AsyncSession, normalized_role: str) -> RoleVocabulary | None:
    return await db.scalar(
        select(RoleVocabulary).where(RoleVocabulary.normalized_role == normalized_role)
    )


async def save_role_vocabulary(
    db: AsyncSession,
    role: str,
    normalized_role: str,
    terms: list[str],
    model_name: str | None,
) -> RoleVocabulary:
    row = RoleVocabulary(
        role=role, normalized_role=normalized_role, terms=terms, model_name=model_name
    )
    db.add(row)
    await db.commit()
    return row
