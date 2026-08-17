from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.companies.models import Company


async def get_or_create_company(
    db: AsyncSession, normalized_name: str, display_name: str
) -> tuple[Company, bool]:
    stmt = (
        pg_insert(Company)
        .values(normalized_name=normalized_name, display_name=display_name)
        .on_conflict_do_nothing(index_elements=["normalized_name"])
        .returning(Company.id)
    )
    result = await db.execute(stmt)
    inserted_id = result.scalar_one_or_none()

    if inserted_id:
        company = (
            await db.execute(select(Company).where(Company.id == inserted_id))
        ).scalar_one()
        return company, True

    company = (
        await db.execute(
            select(Company).where(Company.normalized_name == normalized_name)
        )
    ).scalar_one()
    return company, False
