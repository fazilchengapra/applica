from fastapi import APIRouter
from . import (
    admin_master_cv,
    companies,
    cv_template,
    cv_template_public,
    jobs,
    master_cv,
    matching_jobs,
)

router = APIRouter()

router.include_router(master_cv.router)
router.include_router(jobs.router)
router.include_router(companies.router)
router.include_router(matching_jobs.router)
router.include_router(cv_template.router)
router.include_router(cv_template_public.router)
router.include_router(admin_master_cv.router)
