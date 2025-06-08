from fastapi import FastAPI, APIRouter
from app.core.config import CustomStaticFiles
from fastapi.staticfiles import StaticFiles
from app.api.v1 import user
from app.schemas.base import BizException
from fastapi import Request
from fastapi.responses import JSONResponse
from app.api.internal import router as internal_router
from app.api.v1 import router as v1_router


app = FastAPI(title="SportsX 用户中心")

app.include_router(internal_router, prefix="/api/internal", tags=["internal_api"])
app.include_router(v1_router, prefix="/api/v1", tags=["v1_version_api"])
app.mount("/resources", CustomStaticFiles(directory="resources"), name="resources")

# BizException处理器
@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )
