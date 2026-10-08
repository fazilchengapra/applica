from fastapi import APIRouter
from . import (
    admin_jobs,
    admin_master_cv,
    ats,
    companies,
    cv_template,
    cv_template_public,
    dashboard,
    home,
    jobs,
    master_cv,
    matching_jobs,
    rag,
    tailoring_cv,
)

router = APIRouter()

router.include_router(master_cv.router)
router.include_router(jobs.router)
router.include_router(companies.router)
router.include_router(matching_jobs.router)
router.include_router(rag.router)
router.include_router(cv_template.router)
router.include_router(cv_template_public.router)
router.include_router(admin_master_cv.router)
router.include_router(admin_jobs.router)
router.include_router(tailoring_cv.router)
router.include_router(dashboard.router)
router.include_router(home.router)
router.include_router(ats.router)
