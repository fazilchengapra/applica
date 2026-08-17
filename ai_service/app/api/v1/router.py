from fastapi import APIRouter
from . import master_cv, jobs, companies

router = APIRouter()

router.include_router(master_cv.router)
router.include_router(jobs.router)
router.include_router(companies.router)