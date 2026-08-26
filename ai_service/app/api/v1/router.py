from fastapi import APIRouter
from . import master_cv, jobs, companies, matching_jobs, cv_template, cv_template_public

router = APIRouter()

router.include_router(master_cv.router)
router.include_router(jobs.router)
router.include_router(companies.router)
router.include_router(matching_jobs.router)
router.include_router(cv_template.router)
router.include_router(cv_template_public.router)
