from fastapi import APIRouter
from . import master_cv

router = APIRouter()

router.include_router(master_cv.router)