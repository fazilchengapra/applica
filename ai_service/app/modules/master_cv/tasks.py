import asyncio
from app.core.celery_app import celery_app
from app.db.celery_db import CelerySessionLocal

from app.modules.master_cv.models.master_cv import MasterCVVersion, CVStatus

from app.modules.master_cv.services.helpers.s3_downloader import download_pdf_from_s3
from app.modules.master_cv.services.helpers.text_extractor import extract_pdf
from app.modules.master_cv.services.helpers.cv_structor import structure_cv_text
from app.modules.master_cv.services.helpers.embedder import embed_cv_text
from app.modules.master_cv.services.cv_skill_service import generate_and_insert_skills
from app.modules.notifications.publisher import publish_event


@celery_app.task(name="master_cv.process_cv", bind=True, max_retries=3)
def process_cv_task(self, cv_id: str, s3_key: str, user_id: str):
    asyncio.run(_process_cv_async(cv_id, s3_key, user_id))


async def _process_cv_async(cv_id: str, s3_key: str, user_id: str):
    async with CelerySessionLocal() as session:
        try:
            publish_event(
                event_type="cv.processing",
                user_id=user_id,
                payload={"cv_id": str(cv_id), "status": "processing"},
            )
            pdf_bytes = download_pdf_from_s3(s3_key)
            raw_text = extract_pdf(pdf_bytes)
            structured = structure_cv_text(raw_text)
            embed = await embed_cv_text(raw_text)
            await generate_and_insert_skills(session, cv_id, raw_text)

            version_record = await session.get(MasterCVVersion, cv_id)
            version_record.raw_text = raw_text
            version_record.parsed_data = structured
            version_record.status = CVStatus.COMPLETED
            version_record.embedding = embed
            await session.commit()
            publish_event(
                event_type="cv.completed",
                user_id=user_id,
                payload={
                    "cv_id": str(cv_id),
                    "status": "completed",
                    "title": f"update about your cv {cv_id}",
                    "body": f"your cv id: {cv_id} process completed success",
                },
            )
        except Exception:
            await session.rollback()
            version_record = await session.get(MasterCVVersion, cv_id)
            version_record.status = CVStatus.FAILED
            await session.commit()
            publish_event(
                event_type="cv.failed",
                user_id=user_id,
                payload={
                    "cv_id": str(cv_id),
                    "status": "failed",
                    "title": f"update about your cv {cv_id}",
                    "body": f"your cv id: {cv_id} processing failed",
                },
            )
            raise
