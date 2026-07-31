from fastapi import APIRouter

router = APIRouter(prefix='/master-cv', tags=['master-cv'])

@router.get('/')
def simple_master():
    return {"status": "from master cv"}