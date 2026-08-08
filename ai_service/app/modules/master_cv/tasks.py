import asyncio
from app.core.celery_app import celery_app
from app.db.celery_db import CelerySessionLocal

from app.modules.master_cv.models import MasterCV

from app.modules.master_cv.services.helpers.s3_downloader import download_pdf_from_s3
from app.modules.master_cv.services.helpers.text_extractor import extract_pdf
from app.modules.master_cv.services.helpers.cv_structor import structure_cv_text
from app.modules.master_cv.services.helpers.embedder import embed_cv_text


@celery_app.task(name="master_cv.process_cv", bind=True, max_retries=3)
def process_cv_task(self, cv_id: str, s3_key: str):
    asyncio.run(_process_cv_async(cv_id, s3_key))


async def _process_cv_async(cv_id: str, s3_key: str):
    async with CelerySessionLocal() as session:
        try:
            pdf_bytes = download_pdf_from_s3(s3_key)
            raw_text = extract_pdf(pdf_bytes)
            structured = structure_cv_text(raw_text)
            embed = await embed_cv_text(raw_text)

            print("Embedding type:", type(embed))

            cv_record = await session.get(MasterCV, cv_id)
            cv_record.raw_text = raw_text
            cv_record.parsed_data = structured
            cv_record.status = "completed"
            cv_record.embedding=embed
            await session.commit()
        except Exception:
            await session.rollback()
            cv_record = await session.get(MasterCV, cv_id)
            cv_record.status = "failed"
            await session.commit()
            raise
