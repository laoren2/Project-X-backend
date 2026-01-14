from fastapi import APIRouter, Depends, Query, UploadFile, File
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_admin, get_language, Language
from app.services.asset_manage import (
    query_cpasset_def_service, create_equip_card_def_service,
    create_cpasset_def_service, query_equip_card_def_service,
    add_cpasset_to_shop_service, get_cpassets_in_shop, reward_ccasset_to_user_service,
    get_equip_cards_in_shop, add_equip_card_to_shop_service
)
from app.schemas.asset import (
    CC_CP_PurchaseResultResponse, CPAssetsShopInternalResponse, CPAssetDefResponse,
    CPAssetShopInfoCreateRequest, CPAssetShopInfoUpdateRequest, CPAssetDefCreateForm,
    CCAssetRewardRequest, EquipCardDefCreateForm, EquipCardDefResponse,
    EquipCardShopInfoCreateRequest, EquipCardShopInternalResponse
)
from app.schemas.common import SportType
from app.core.errors import ErrorCode
from app.schemas.base import BaseResponse, BizException
from app.schemas.user import AuthContext
import uuid


router = APIRouter(dependencies=[Depends(get_language)])


@router.get("/query_cpassets_in_shop",response_model=BaseResponse[CPAssetsShopInternalResponse], summary="查询商店的通用道具资产信息")
async def query_cpassets_in_shop(
    name: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    is_on_shelves: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await get_cpassets_in_shop(db, name, asset_id, is_on_shelves, page, size)
    return BaseResponse.success(token=auth.new_token, data=result)


@router.post("/add_cpasset_to_shop",response_model=BaseResponse[None], summary="将通用道具资产上架到商店")
async def add_cpasset_to_shop(
    request: CPAssetShopInfoCreateRequest,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await add_cpasset_to_shop_service(db, request)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)


#@router.post("/update_cpasset_in_shop",response_model=BaseResponse[None], summary="更新通用道具资产在商店的信息")
#async def update_cpasset_in_shop(
#    request: CPAssetShopInfoUpdateRequest,
#    auth: AuthContext = Depends(get_current_admin),
#    db: AsyncSession = Depends(get_db)
#):
#    await update_cpasset_in_shop_service(db, request.asset_id, request.price)
#    return BaseResponse.success(token=auth.new_token, message="更新成功", data=None)


@router.get("/query_cpasset_def",response_model=BaseResponse[CPAssetDefResponse], summary="查询通用道具资产定义")
async def query_cpasset_def(
    name: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await query_cpasset_def_service(db, name, type, page, size)
    return BaseResponse.success(token=auth.new_token, message="success", data=result)


@router.post("/create_cpasset_def",response_model=BaseResponse[None],summary="创建新道具定义")
async def create_cpasset_def(
    form: CPAssetDefCreateForm = Depends(CPAssetDefCreateForm.as_form),
    image: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    asset_id = f"cpasset_{str(uuid.uuid4())[:8]}"

    cpasset_folder = Path("resources/asset/cpasset") / asset_id
    cpasset_folder.mkdir(parents=True, exist_ok=True)
    for file in cpasset_folder.glob("cover_*.jpg"):
        file.unlink(missing_ok=True)
    cover_path = cpasset_folder / f"cover_{int(datetime.now().timestamp())}.jpg"
    contents = await image.read()
    if len(contents) > 0.5 * 1024 * 1024:  # 超过 512KB
        raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
    with cover_path.open("wb") as f:
        f.write(contents)
    new_url = f"/resources/asset/cpasset/{asset_id}/{cover_path.name}"
    await create_cpasset_def_service(db, form, asset_id, new_url)

    return BaseResponse.success(token=auth.new_token, message="success", data=None)


@router.post("/reward_ccasset",response_model=BaseResponse[None],summary="用户通用货币资产奖励")
async def reward_ccasset_to_user(
    request: CCAssetRewardRequest,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await reward_ccasset_to_user_service(db, request)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)


@router.get("/query_equip_card_def",response_model=BaseResponse[EquipCardDefResponse], summary="查询卡牌资产定义")
async def query_equip_card_def(
    name: Optional[str] = Query(None),
    sport_type: Optional[SportType] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await query_equip_card_def_service(db, name, sport_type, page, size)
    return BaseResponse.success(token=auth.new_token, message="success", data=result)


@router.post("/create_equip_card_def",response_model=BaseResponse[None],summary="创建新卡牌定义")
async def create_equip_card_def(
    form: EquipCardDefCreateForm = Depends(EquipCardDefCreateForm.as_form),
    image: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    asset_id = f"equipcard_def_{str(uuid.uuid4())[:8]}"

    cpasset_folder = Path("resources/asset/equipcard") / asset_id
    cpasset_folder.mkdir(parents=True, exist_ok=True)
    for file in cpasset_folder.glob("cover_*.jpg"):
        file.unlink(missing_ok=True)
    cover_path = cpasset_folder / f"cover_{int(datetime.now().timestamp())}.jpg"
    contents = await image.read()
    if len(contents) > 0.5 * 1024 * 1024:  # 超过 512KB
        raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
    with cover_path.open("wb") as f:
        f.write(contents)
    new_url = f"/resources/asset/equipcard/{asset_id}/{cover_path.name}"
    await create_equip_card_def_service(db, form, asset_id, new_url)

    return BaseResponse.success(token=auth.new_token, message="success", data=None)


@router.get("/query_equip_cards_in_shop",response_model=BaseResponse[EquipCardShopInternalResponse], summary="查询商店的卡牌信息")
async def query_equip_cards_in_shop(
    name: Optional[str] = Query(None),
    card_def_id: Optional[str] = Query(None),
    is_on_shelves: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await get_equip_cards_in_shop(db, name, card_def_id, is_on_shelves, page, size)
    return BaseResponse.success(token=auth.new_token, data=result)


@router.post("/add_equip_card_to_shop",response_model=BaseResponse[None], summary="将卡牌上架到商店")
async def add_equip_card_to_shop(
    request: EquipCardShopInfoCreateRequest,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await add_equip_card_to_shop_service(db, request)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)