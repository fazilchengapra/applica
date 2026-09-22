from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.companies.models import Company, CompanyStatus
from app.modules.companies.services.verify_company import get_company_or_raise


async def list_companies(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> list[Company]:
    stmt = select(Company)
    if status:
        stmt = stmt.where(Company.status == status)
    stmt = stmt.order_by(Company.verified_at.desc().nullslast(), Company.normalized_name.asc())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_company_detail(db: AsyncSession, company_id: UUID) -> Company:
    return await get_company_or_raise(db, company_id)


async def admin_approve_company(db: AsyncSession, company_id: UUID) -> Company:
    company = await get_company_or_raise(db, company_id)
    company.status = CompanyStatus.ADMIN_VERIFIED.value
    company.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(company)
    return company


async def admin_reject_company(db: AsyncSession, company_id: UUID) -> Company:
    company = await get_company_or_raise(db, company_id)
    company.status = CompanyStatus.REJECTED.value
    company.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(company)
    return company