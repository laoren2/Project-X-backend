from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.asset_manage import (
    get_user_ccassets, get_user_cpassets, buy_cpassets_use_ccasset, get_cpassets_on_shelves,
    get_user_cpasset
)
from app.schemas.asset import (
    CCAssetsResponse, CPAssetsResponse, CPAssetBuyRequest, 
    CC_CP_PurchaseResultResponse, CPAssetsShopResponse, CPAssetBaseInfo
)
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
import uuid


router = APIRouter()



@router.get("/query_cpassets_on_shelves",response_model=BaseResponse[CPAssetsShopResponse], summary="查询商店的通用道具资产信息")
async def query_cpassets_on_shelves(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_cpassets_on_shelves(db)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询用户所有ccasset 金币 & 点券 & 金券资产
@router.get("/query_user_ccassets",response_model=BaseResponse[CCAssetsResponse], summary="查询用户所有通用货币资产")
async def query_user_ccassets(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_user_ccassets(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询用户所有cpasset
@router.get("/query_user_cpassets",response_model=BaseResponse[CPAssetsResponse], summary="查询用户所有通用道具资产")
async def query_user_cpassets(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assets = await get_user_cpassets(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=assets)

# 查询用户指定cpasset
@router.get("/query_user_cpasset",response_model=BaseResponse[CPAssetBaseInfo], summary="查询用户指定通用道具资产")
async def query_user_cpasset(
    asset_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    asset = await get_user_cpasset(db, auth.payload["user_id"], asset_id)
    return BaseResponse.success(token=auth.new_token, data=asset)

# 购买cpasset
@router.post("/buy_cpasset",response_model=BaseResponse[CC_CP_PurchaseResultResponse],summary="购买通用道具资产")
async def buy_cpasset(
    request: CPAssetBuyRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await buy_cpassets_use_ccasset(
        db, auth.payload["user_id"], request.cpasset_id, request.cpamount
    )
    return BaseResponse.success(token=auth.new_token, data=result, message="购买成功")
