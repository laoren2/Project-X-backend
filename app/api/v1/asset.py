from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_user, get_language
from app.services.asset_manage import (
    get_user_ccassets, get_user_cpassets, buy_cpassets_use_ccasset, get_cpassets_on_shelves,
    get_user_cpasset, get_equip_cards_on_shelves, get_user_equip_cards, buy_equip_card_use_ccasset,
    upgrade_equip_card_mat_service, upgrade_equip_card_fusion_service, get_equip_card_upgrade_price_service,
    upgrade_equip_card_skill1_service, get_equip_card_skill1_upgrade_price_service, get_equip_card_skill2_upgrade_price_service,
    get_equip_card_skill3_upgrade_price_service, upgrade_equip_card_skill2_service, upgrade_equip_card_skill3_service,
    destroy_equip_card_service, get_user_equip_card_detail_service, get_equip_card_shop_detail_service
)
from app.schemas.asset import (
    CCAssetsResponse, CPAssetsResponse, CPAssetBuyRequest, 
    CC_CP_PurchaseResultResponse, CPAssetsShopResponse, CPAssetBaseInfo, EquipCardShopInfo,
    EquipCardShopResponse, EquipCardsResponse, CC_ECARD_PurchaseResultResponse,
    EquipCardUpgradeResponse, EquipCardUpgradePriceInfo, EquipCardSkillUpgradeResponse
)
from app.schemas.common import EquipCardBaseInfo, CCAssetBaseInfo
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
import uuid


router = APIRouter(dependencies=[Depends(get_language)])



@router.get("/query_cpassets_on_shelves",response_model=BaseResponse[CPAssetsShopResponse], summary="查询商店已上架的通用道具资产信息")
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

@router.get("/query_equip_card_shop_detail",response_model=BaseResponse[EquipCardShopInfo], summary="查询商店的卡牌信息")
async def query_equip_card_shop_detail(
    def_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    card = await get_equip_card_shop_detail_service(db, def_id)
    return BaseResponse.success(token=auth.new_token, data=card)

@router.get("/query_equip_cards_on_shelves",response_model=BaseResponse[EquipCardShopResponse], summary="查询商店已上架的所有卡牌信息")
async def query_equip_cards_on_shelves(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_equip_cards_on_shelves(db)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询用户卡牌详细信息
@router.get("/query_user_equip_card_detail",response_model=BaseResponse[EquipCardBaseInfo], summary="查询用户卡牌详细信息")
async def query_user_equip_card_detail(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    card = await get_user_equip_card_detail_service(db, card_id)
    return BaseResponse.success(token=auth.new_token, data=card)

# 查询用户所有卡牌
@router.get("/query_user_equip_cards",response_model=BaseResponse[EquipCardsResponse], summary="查询用户所有卡牌资产")
async def query_user_equip_cards(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assets = await get_user_equip_cards(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=assets)

# 购买卡牌
@router.post("/buy_equip_card",response_model=BaseResponse[CC_ECARD_PurchaseResultResponse],summary="购买卡牌")
async def buy_equip_card(
    card_def_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await buy_equip_card_use_ccasset(db, auth.payload["user_id"], card_def_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="购买成功")

# 销毁卡牌
@router.post("/destroy_equip_card",response_model=BaseResponse[EquipCardUpgradePriceInfo],summary="销毁卡牌")
async def destroy_equip_card(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await destroy_equip_card_service(db, auth.payload["user_id"], card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="销毁成功")

# 查询升级材料价格
@router.get("/query_equip_card_upgrade_price",response_model=BaseResponse[EquipCardUpgradePriceInfo], summary="查询升级卡牌的材料价格")
async def query_equip_card_upgrade_price(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assets = await get_equip_card_upgrade_price_service(db, card_id)
    return BaseResponse.success(token=auth.new_token, data=assets)


# 查询技能升级材料价格
@router.get("/query_equip_card_skill1_upgrade_price",response_model=BaseResponse[CCAssetBaseInfo], summary="查询升级卡牌技能1的材料价格")
async def query_equip_card_skill1_upgrade_price(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    price = await get_equip_card_skill1_upgrade_price_service(db, card_id)
    return BaseResponse.success(token=auth.new_token, data=price)

@router.get("/query_equip_card_skill2_upgrade_price",response_model=BaseResponse[CCAssetBaseInfo], summary="查询升级卡牌技能2的材料价格")
async def query_equip_card_skill2_upgrade_price(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    price = await get_equip_card_skill2_upgrade_price_service(db, card_id)
    return BaseResponse.success(token=auth.new_token, data=price)

@router.get("/query_equip_card_skill3_upgrade_price",response_model=BaseResponse[CCAssetBaseInfo], summary="查询升级卡牌技能3的材料价格")
async def query_equip_card_skill3_upgrade_price(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    price = await get_equip_card_skill3_upgrade_price_service(db, card_id)
    return BaseResponse.success(token=auth.new_token, data=price)


# 升级卡牌（材料）
@router.post("/upgrade_equip_card_mat",response_model=BaseResponse[EquipCardUpgradeResponse],summary="材料升级卡牌")
async def upgrade_equip_card_mat(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await upgrade_equip_card_mat_service(db, auth.payload["user_id"], card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="升级成功")

# 升级卡牌（融合）
@router.post("/upgrade_equip_card_fusion",response_model=BaseResponse[EquipCardBaseInfo],summary="融合升级卡牌")
async def upgrade_equip_card_fusion(
    card_id: str = Query(...),
    fusion_card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await upgrade_equip_card_fusion_service(db, card_id, fusion_card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="升级成功")

# 升级卡牌技能
@router.post("/upgrade_equip_card_skill1",response_model=BaseResponse[EquipCardSkillUpgradeResponse],summary="升级卡牌技能1")
async def upgrade_equip_card_skill1(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await upgrade_equip_card_skill1_service(db, auth.payload["user_id"], card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="升级成功")

@router.post("/upgrade_equip_card_skill2",response_model=BaseResponse[EquipCardSkillUpgradeResponse],summary="升级卡牌技能2")
async def upgrade_equip_card_skill2(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await upgrade_equip_card_skill2_service(db, auth.payload["user_id"], card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="升级成功")

@router.post("/upgrade_equip_card_skill3",response_model=BaseResponse[EquipCardSkillUpgradeResponse],summary="升级卡牌技能3")
async def upgrade_equip_card_skill3(
    card_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await upgrade_equip_card_skill3_service(db, auth.payload["user_id"], card_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="升级成功")


