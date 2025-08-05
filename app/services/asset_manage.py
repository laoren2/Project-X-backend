from app.crud.asset_manage import (
    get_or_create_user_ccasset, get_cpasset_price,
    update_user_ccasset_balance, create_ccasset_transaction, 
    get_or_create_user_cpasset, update_user_cpasset_balance, create_cpasset_transaction,
    get_user_cpasset_all, get_cpasset_def_by_asset_id, get_cpasset_on_shelves,
    insert_cp_asset_def_and_child, query_cpasset_def_crud, query_cpassets_in_shop_crud,
    add_cpasset_to_shop_crud, consume_ccasset, consume_cpasset,
    reward_ccasset, reward_cpasset
)
from app.crud.user import get_user_by_id
from app.db.models.asset import CPRegistrationCardDef, CPTeamCardDef, CPAssetDef, CPAssetPrice
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from app.schemas.asset import (
    CCAssetsResponse, CCAssetType, AssetOperation, CPAssetType, CPAssetsResponse, 
    CPAssetBaseInfo, CC_CP_PurchaseResultResponse, CC_CC_PurchaseResultResponse, CPAssetsShopResponse, CPAssetShopInfo,
    CPAssetDefCreateForm, CPAssetDefInfo, CPAssetDefResponse, CPAssetShopInfoCreateRequest, 
    CPAssetsShopInternalResponse, CPAssetShopInternalInfo, CCAssetRewardRequest
)
from app.core.tools import auto_cast_fields
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
import json


# 子类映射表
CP_ASSET_SUBCLASS_MAP = {
    CPAssetType.registration_card: CPRegistrationCardDef,
    CPAssetType.team_card: CPTeamCardDef
    # 后续新增类型只需在这里添加映射
}

# 字段验证规则
CP_ASSET_FIELD_VALIDATION = {
    CPAssetType.registration_card: {
        "required": ["sport_type", "is_team"],
        "optional": []
    },
    CPAssetType.team_card: {
        "required": ["sport_type"],
        "optional": []
    }
}


# 高并发重复购买情况下，可能导致客户端状态更新错乱，暂在客户端防抖+手动刷新兜底解决，但无法避免多客户端同一用户同时购买情况
async def buy_cpassets_use_ccasset(
    db: AsyncSession,
    user_id: str,
    cpasset_id: str,
    cpamount: int
) -> CC_CP_PurchaseResultResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        cpasset_def = await get_cpasset_def_by_asset_id(db, cpasset_id)
        if cpasset_def is None:
            raise BizException(code=ErrorCode.ASSET_DEF_ERROR, message="找不到资产定义")
        # 查询当前cpasset对应的ccasset类型和价格
        cpasset_price = await get_cpasset_price(db, cpasset_def.id)
        if cpasset_price is None:
            raise BizException(code=ErrorCode.PRODUCT_REMOVED_FROM_SHELVES, message="商品已下架")
        ccasset_type = cpasset_price.ccasset_type
        ccamount = cpasset_price.price
    
        cpasset = await get_or_create_user_cpasset(db, user.id, cpasset_def.id)
        new_ccsset_balance = await consume_ccasset(db, ccasset_type, ccamount * cpamount, user.id, f"购买 {cpamount} {cpasset_def.prop_type.display_name()}")
        new_cpasset_balance = cpasset.balance + cpamount
        await update_user_cpasset_balance(db, cpasset, new_cpasset_balance)
        await create_cpasset_transaction(
            db, user.id, cpasset_def.id, AssetOperation.CONSUME, cpamount, new_cpasset_balance, description=f"purchase from {ccamount * cpamount} {ccasset_type.display_name()}"
        )
        return CC_CP_PurchaseResultResponse(
            ccasset_type=ccasset_type,
            new_ccamount=new_ccsset_balance,
            cpasset_id=cpasset_id,
            new_cpamount=new_cpasset_balance
        )


# 查询用户所有cc资产
async def get_user_ccassets(db: AsyncSession, user_id: str) -> CCAssetsResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    coin = await get_or_create_user_ccasset(db, user.id, CCAssetType.COIN)
    coupon = await get_or_create_user_ccasset(db, user.id, CCAssetType.COUPON)
    voucher = await get_or_create_user_ccasset(db, user.id, CCAssetType.VOUCHER)
    await db.commit()
    return CCAssetsResponse(
        coin_amount=coin.balance,
        coupon_amount=coupon.balance,
        voucher_amount=voucher.balance
    )


# 查询用户指定cp资产
async def get_user_cpasset(db: AsyncSession, user_id: str, asset_id: str) -> CPAssetBaseInfo:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    cpasset_def = await get_cpasset_def_by_asset_id(db, asset_id)
    if cpasset_def is None:
        raise BizException(code=ErrorCode.ASSET_DEF_ERROR, message="找不到资产定义")
    cpasset = await get_or_create_user_cpasset(db, user.id, cpasset_def.id)
    await db.commit()
    result = CPAssetBaseInfo(
        asset_id=cpasset_def.asset_id,
        name=cpasset_def.name,
        description=cpasset_def.description,
        image_url=cpasset_def.image_url,
        amount=cpasset.balance
    )
    return result


# 查询用户所有cp资产
async def get_user_cpassets(db: AsyncSession, user_id: str) -> CPAssetsResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    cpassets = await get_user_cpasset_all(db, user.id)
    assets = []
    for asset in cpassets:
        prop_def = asset.prop_def
        if prop_def is not None and asset.balance > 0:
            assets.append(
                CPAssetBaseInfo(
                    asset_id=prop_def.asset_id,
                    name=prop_def.name,
                    description=prop_def.description,
                    image_url=prop_def.image_url,
                    amount=asset.balance
                )
            )
    return CPAssetsResponse(assets=assets)

# 查询商店的通用道具资产信息
async def get_cpassets_on_shelves(db: AsyncSession) -> CPAssetsShopResponse:
    cpassets = await get_cpasset_on_shelves(db)
    assets = []
    for asset in cpassets:
        prop_def = asset.prop_def
        if prop_def is not None:
            assets.append(
                CPAssetShopInfo(
                    asset_id=prop_def.asset_id,
                    name=prop_def.name,
                    description=prop_def.description,
                    image_url=prop_def.image_url,
                    ccasset_type=asset.ccasset_type,
                    price=asset.price
                )
            )
    return CPAssetsShopResponse(assets=assets)

async def get_cpassets_in_shop(
        db: AsyncSession, 
        name: Optional[str], 
        asset_id: Optional[str],
        is_on_shelves: Optional[str],
        page: int, 
        size: int
) -> CPAssetsShopInternalResponse:
    cpassets = await query_cpassets_in_shop_crud(db, name, asset_id, is_on_shelves, page, size)
    assets = []
    for asset in cpassets:
        prop_def = asset.prop_def
        if prop_def is not None:
            assets.append(
                CPAssetShopInternalInfo(
                    asset_id=prop_def.asset_id,
                    name=prop_def.name,
                    description=prop_def.description,
                    image_url=prop_def.image_url,
                    ccasset_type=asset.ccasset_type,
                    price=asset.price,
                    is_on_shelves=asset.is_on_shelves
                )
            )
    return CPAssetsShopInternalResponse(assets=assets)

async def add_cpasset_to_shop_service(db: AsyncSession, request: CPAssetShopInfoCreateRequest):
    cpasset_def = await get_cpasset_def_by_asset_id(db, request.asset_id)
    if cpasset_def is None:
        raise BizException(code=ErrorCode.ASSET_DEF_ERROR, message="找不到资产定义")
    cpasset_price = CPAssetPrice(
        prop_def_id = cpasset_def.id,
        ccasset_type = request.ccasset_type,
        price = request.price,
        is_on_shelves = request.is_on_shelves
    )
    await add_cpasset_to_shop_crud(db, cpasset_price)
    await db.commit()

# 查询cp道具定义
async def query_cpasset_def_service(db: AsyncSession, name: Optional[str], prop_type: Optional[str], page: int, size: int):
    items = await query_cpasset_def_crud(db, name, prop_type, page, size)
    # 转换为 schema
    defs = [
        CPAssetDefInfo(
            asset_id=item.asset_id,
            cpasset_type=item.prop_type,
            name=item.name,
            description=item.description,
            image_url=item.image_url
        )
        for item in items
    ]
    return CPAssetDefResponse(defs=defs)


# 创建新道具定义
async def create_cpasset_def_service(
    db: AsyncSession, 
    form: CPAssetDefCreateForm, 
    asset_id: str, 
    url: str
):
    async with db.begin():
        extra_fields_dict = json.loads(form.extra_fields)
        parent_data = {
            "asset_id": asset_id,
            "prop_type": form.prop_type,
            "name": form.name,
            "description": form.description,
            "image_url": url
        }
        # 3. 动态创建子类实例并插入
        await create_cp_asset_def_with_subclass(db, parent_data, extra_fields_dict)


async def create_cp_asset_def_with_subclass(db: AsyncSession, parent_data: dict, extra_fields: dict):
    # 1. prop_type 统一为 CPAssetType 枚举
    prop_type = parent_data["prop_type"]
    if isinstance(prop_type, str):
        try:
            prop_type = CPAssetType(prop_type)
            parent_data["prop_type"] = prop_type
        except ValueError:
            raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"prop_type字段非法")

    # 2. 获取子类
    print("prop_type:", prop_type, type(prop_type))
    print("CP_ASSET_SUBCLASS_MAP keys:", list(CP_ASSET_SUBCLASS_MAP.keys()))
    subclass = CP_ASSET_SUBCLASS_MAP.get(prop_type)
    if not subclass:
        raise BizException(code=ErrorCode.TABLE_NOT_FOUND, message=f"找不到相应表")

    # 3. 校验必填字段
    validation_rules = CP_ASSET_FIELD_VALIDATION.get(prop_type, {})
    required_fields = validation_rules.get("required", [])
    for field in required_fields:
        if field not in extra_fields:
            raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"extra_fields字段错误")
    filtered_data = {k: v for k, v in extra_fields.items() if k in required_fields}
    filtered_data = auto_cast_fields(subclass, filtered_data)

    await insert_cp_asset_def_and_child(db, parent_data, subclass, filtered_data)


async def reward_ccasset_to_user_service(db: AsyncSession, request: CCAssetRewardRequest) -> int:
    async with db.begin():
        user = await get_user_by_id(db, request.user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        new_balance = await reward_ccasset(db, request.ccasset_type, request.amount, user.id, "系统奖励")
        return new_balance

