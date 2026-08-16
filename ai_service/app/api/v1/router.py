from fastapi import APIRouter
from . import master_cv, jobs

router = APIRouter()

router.include_router(master_cv.router)
router.include_router(jobs.router)