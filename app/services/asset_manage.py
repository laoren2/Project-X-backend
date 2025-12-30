from app.crud.asset_manage import (
    get_equip_card_by_card_id, get_or_create_user_ccasset, get_cpasset_price_on_shelves,
    update_user_ccasset_balance, create_ccasset_transaction, 
    get_or_create_user_cpasset, update_user_cpasset_balance, create_cpasset_transaction,
    get_user_cpasset_all, get_cpasset_def_by_asset_id, get_cpassets_on_shelves_crud,
    insert_cp_asset_def_and_child, query_cpasset_def_crud, query_cpassets_in_shop_crud,
    add_cpasset_to_shop_crud, consume_ccasset, consume_cpasset,
    reward_ccasset, reward_cpasset, query_equip_card_def_crud, get_user_equip_cards_all,
    query_equip_cards_in_shop_crud, get_equip_card_def_by_card_id, get_equip_cards_on_shelves_crud,
    get_equip_card_price_on_shelves, create_user_equip_card, create_equip_card_transaction
)
from app.crud.user import get_user_by_id
from app.db.models.asset import CPRegistrationCardDef, CPTeamCardDef, CPAssetDef, CPAssetPrice, EquipmentCardDef, EquipCardPrice, UserEquipmentCard
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from app.schemas.asset import (
    CCAssetsResponse, AssetOperation, CPAssetType, CPAssetsResponse,
    CPAssetBaseInfo, CC_CP_PurchaseResultResponse, CC_CC_PurchaseResultResponse, CPAssetsShopResponse, CPAssetShopInfo,
    CPAssetDefCreateForm, CPAssetDefInfo, CPAssetDefResponse, CPAssetShopInfoCreateRequest, 
    CPAssetsShopInternalResponse, CPAssetShopInternalInfo, CCAssetRewardRequest,
    EquipCardDefCreateForm, EquipCardDefInfo, EquipCardDefResponse, EquipCardShopInternalResponse,
    EquipCardShopInfoCreateRequest, EquipCardShopInternalInfo, EquipCardShopResponse,
    EquipCardShopInfo, EquipCardsResponse, CC_ECARD_PurchaseResultResponse,
    EquipCardUpgradeResponse, EquipCardUpgradePriceInfo,
    EquipCardSkillUpgradeResponse
)
from app.schemas.common import EquipCardBaseInfo, SportType, CCAssetType, CCAssetBaseInfo
from app.services.mappers import equip_card_to_base_info
from app.core.tools import auto_cast_fields
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid, random, math, json


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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        cpasset_def = await get_cpasset_def_by_asset_id(db, cpasset_id)
        if cpasset_def is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        # 查询当前cpasset对应的ccasset类型和价格
        cpasset_price = await get_cpasset_price_on_shelves(db, cpasset_def.id)
        if cpasset_price is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.off_shelves")
        ccasset_type = cpasset_price.ccasset_type
        ccamount = cpasset_price.price
    
        cpasset = await get_or_create_user_cpasset(db, user.id, cpasset_def.id)
        new_ccasset_balance = await consume_ccasset(db, ccasset_type, ccamount * cpamount, user.id, f"购买 {cpamount} {cpasset_def.prop_type.display_name()}")
        new_cpasset_balance = cpasset.balance + cpamount
        await update_user_cpasset_balance(db, cpasset, new_cpasset_balance)
        await create_cpasset_transaction(
            db, user.id, cpasset_def.id, AssetOperation.CONSUME, cpamount, new_cpasset_balance, description=f"消费 {ccamount * cpamount} {ccasset_type.display_name()} 购买"
        )
        return CC_CP_PurchaseResultResponse(
            ccasset_type=ccasset_type,
            new_ccamount=new_ccasset_balance,
            cpasset_id=cpasset_id,
            new_cpamount=new_cpasset_balance
        )


# 查询用户所有cc资产
async def get_user_ccassets(db: AsyncSession, user_id: str) -> CCAssetsResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        coin = await get_or_create_user_ccasset(db, user.id, CCAssetType.COIN)
        coupon = await get_or_create_user_ccasset(db, user.id, CCAssetType.COUPON)
        voucher = await get_or_create_user_ccasset(db, user.id, CCAssetType.VOUCHER)
        stone1 = await get_or_create_user_ccasset(db, user.id, CCAssetType.STONE1)
        stone2 = await get_or_create_user_ccasset(db, user.id, CCAssetType.STONE2)
        stone3 = await get_or_create_user_ccasset(db, user.id, CCAssetType.STONE3)
        return CCAssetsResponse(
            coin_amount=coin.balance,
            coupon_amount=coupon.balance,
            voucher_amount=voucher.balance,
            stone1_amount=stone1.balance,
            stone2_amount=stone2.balance,
            stone3_amount=stone3.balance
        )


# 查询用户指定cp资产
async def get_user_cpasset(db: AsyncSession, user_id: str, asset_id: str) -> CPAssetBaseInfo:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    cpasset_def = await get_cpasset_def_by_asset_id(db, asset_id)
    if cpasset_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
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
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
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
    cpassets = await get_cpassets_on_shelves_crud(db)
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
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
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
        try:
            extra_fields_dict = json.loads(form.extra_fields)
        except json.JSONDecodeError:
            raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")
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
    #print("prop_type:", prop_type, type(prop_type))
    #print("CP_ASSET_SUBCLASS_MAP keys:", list(CP_ASSET_SUBCLASS_MAP.keys()))
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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        new_balance = await reward_ccasset(db, request.ccasset_type, request.amount, user.id, "系统奖励", AssetOperation.REWARD)
        return new_balance


# 查询卡牌定义
async def query_equip_card_def_service(
    db: AsyncSession, 
    name: Optional[str], 
    sport_type: Optional[SportType], 
    page: int, 
    size: int
) -> EquipCardDefResponse:
    items = await query_equip_card_def_crud(db, name, sport_type, page, size)
    defs = [EquipCardDefInfo.model_validate(item) for item in items]
    return EquipCardDefResponse(defs=defs)


async def create_equip_card_def_service(
    db: AsyncSession, 
    form: EquipCardDefCreateForm, 
    def_id: str, 
    url: str
):
    try:
        tags_data = json.loads(form.tags)
        effect_data = json.loads(form.effect_config)
    except json.JSONDecodeError:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")
    card = EquipmentCardDef(
        def_id=def_id,
        name=form.name,
        sport_type=form.sport_type,
        rarity=form.rarity,
        description=form.description,
        skill1_description=form.skill1_description,
        skill2_description=form.skill2_description,
        skill3_description=form.skill3_description,
        image_url=url,
        version=form.version,
        #type_name=form.type_name,
        tags=tags_data,
        effect_config=effect_data,
    )
    db.add(card)
    await db.commit()


async def get_equip_cards_in_shop(
    db: AsyncSession,
    name: Optional[str],
    card_id: Optional[str],
    is_on_shelves: Optional[str],
    page: int,
    size: int
) -> EquipCardShopInternalResponse:
    quip_cards = await query_equip_cards_in_shop_crud(db, name, card_id, is_on_shelves, page, size)
    cards = []
    for card in quip_cards:
        card_def = card.card_def
        if card_def is not None:
            cards.append(
                EquipCardShopInternalInfo(
                    def_id=card_def.def_id,
                    name=card_def.name,
                    image_url=card_def.image_url,
                    sport_type=card_def.sport_type,
                    rarity=card_def.rarity,
                    description=card_def.description,
                    skill1_description=card_def.skill1_description,
                    skill2_description=card_def.skill2_description,
                    skill3_description=card_def.skill3_description,
                    version=card_def.version,
                    effect_config=card_def.effect_config,
                    ccasset_type=card.ccasset_type,
                    price=card.price,
                    is_on_shelves=card.is_on_shelves
                )
            )
    return EquipCardShopInternalResponse(cards=cards)

async def add_equip_card_to_shop_service(db: AsyncSession, request: EquipCardShopInfoCreateRequest):
    equip_card_def = await get_equip_card_def_by_card_id(db, request.card_def_id)
    if equip_card_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    equip_card_price = EquipCardPrice(
        def_id = equip_card_def.id,
        ccasset_type = request.ccasset_type,
        price = request.price,
        is_on_shelves = request.is_on_shelves
    )
    db.add(equip_card_price)
    await db.commit()

# 查询商店的卡牌信息
async def get_equip_cards_on_shelves(db: AsyncSession) -> EquipCardShopResponse:
    card_prices = await get_equip_cards_on_shelves_crud(db)
    cards = []
    for price in card_prices:
        card_def = price.card_def
        if card_def is not None:
            cards.append(
                EquipCardShopInfo(
                    def_id=card_def.def_id,
                    name=card_def.name,
                    image_url=card_def.image_url,
                    sport_type=card_def.sport_type,
                    rarity=card_def.rarity,
                    description=card_def.description,
                    skill1_description=card_def.skill1_description,
                    skill2_description=card_def.skill2_description,
                    skill3_description=card_def.skill3_description,
                    version=card_def.version,
                    effect_config=card_def.effect_config,
                    ccasset_type=price.ccasset_type,
                    price=price.price
                )
            )
    return EquipCardShopResponse(cards=cards)

# 查询用户持有卡牌
async def get_user_equip_cards(db: AsyncSession, user_id: str) -> EquipCardsResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    user_cards = await get_user_equip_cards_all(db, user.id)
    cards = []
    for card in user_cards:
        card_info = equip_card_to_base_info(card)
        if card_info is not None:
            cards.append(card_info)
    return EquipCardsResponse(cards=cards)

async def buy_equip_card_use_ccasset(
    db: AsyncSession,
    user_id: str,
    card_def_id: str
) -> CC_ECARD_PurchaseResultResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card_def = await get_equip_card_def_by_card_id(db, card_def_id)
        if card_def is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        # 查询当前cpasset对应的ccasset类型和价格
        equip_card_price = await get_equip_card_price_on_shelves(db, card_def.id)
        if equip_card_price is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.off_shelves")
        ccasset_type = equip_card_price.ccasset_type
        ccamount = equip_card_price.price
    
        equip_card = await create_user_equip_card(db, user.id, card_def)
        new_ccasset_balance = await consume_ccasset(db, ccasset_type, ccamount, user.id, f"购买 {card_def.name}")
        await create_equip_card_transaction(
            db, user.id, equip_card.id, card_def.id, AssetOperation.CONSUME, 1, description=f"消费 {ccamount} {ccasset_type.display_name()} 购买"
        )
        card_info = EquipCardBaseInfo(
            card_id=equip_card.card_id,
            def_id=card_def.def_id,
            name=card_def.name,
            sport_type=card_def.sport_type,
            level=equip_card.level,
            levelSkill1=equip_card.skill1_level,
            levelSkill2=equip_card.skill2_level,
            levelSkill3=equip_card.skill3_level,
            image_url=card_def.image_url,
            lucky=equip_card.lucky_value,
            rarity=card_def.rarity,
            description=card_def.description,
            description_skill1=card_def.skill1_description,
            description_skill2=card_def.skill2_description,
            description_skill3=card_def.skill3_description,
            multiplier=equip_card.multiplier,
            multiplier_skill1=equip_card.multiplier_skill1,
            multiplier_skill2=equip_card.multiplier_skill2,
            multiplier_skill3=equip_card.multiplier_skill3,
            version=card_def.version,
            #type_name=card_def.type_name,
            tags=card_def.tags,
            effect_def=card_def.effect_config
        )
        return CC_ECARD_PurchaseResultResponse(
            ccasset_type=ccasset_type,
            new_ccamount=new_ccasset_balance,
            card=card_info
        )

def get_card_destroy_price(card: UserEquipmentCard) -> List[CCAssetBaseInfo]:
    if card.equipment_def is None:
        return []
    if card.equipment_def.rarity == "C":
        amount = 100
    elif card.equipment_def.rarity == "B":
        amount = 500
    elif card.equipment_def.rarity == "A":
        amount = 1000
    else:
        amount = 2000
    result = [
        CCAssetBaseInfo(ccasset_type=CCAssetType.COIN, new_ccamount=amount),
        CCAssetBaseInfo(ccasset_type=CCAssetType.VOUCHER, new_ccamount=amount),
        CCAssetBaseInfo(ccasset_type=CCAssetType.COUPON, new_ccamount=amount),
        CCAssetBaseInfo(ccasset_type=CCAssetType.STONE1, new_ccamount=amount/10),
        CCAssetBaseInfo(ccasset_type=CCAssetType.STONE2, new_ccamount=amount/10),
        CCAssetBaseInfo(ccasset_type=CCAssetType.STONE3, new_ccamount=amount/10)
    ]
    return result

async def destroy_equip_card_service(
    db: AsyncSession,
    user_id: str,
    card_id: str
) -> EquipCardUpgradePriceInfo:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None or card.user_id != user.id:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.equipment_def is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        prices = get_card_destroy_price(card)
        result = []
        for price in prices:
            new_balance = await reward_ccasset(db, price.ccasset_type, price.new_ccamount, user.id, "销毁卡牌获得", AssetOperation.DESTROY)
            result.append(CCAssetBaseInfo(ccasset_type=price.ccasset_type, new_ccamount=new_balance))
        await create_equip_card_transaction(db, user.id, card.id, card.equipment_def.id, AssetOperation.DESTROY, 0, description=f"销毁卡牌 {card.equipment_def.name}")
        await db.delete(card)
        return EquipCardUpgradePriceInfo(prices=result)

# 查询卡牌升级价格
async def get_equip_card_upgrade_price_service(db: AsyncSession, card_id: str) -> EquipCardUpgradePriceInfo:
    card = await get_equip_card_by_card_id(db, card_id)
    if card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
    prices = get_card_upgrade_price(card)
    return EquipCardUpgradePriceInfo(prices=prices)

# 查询技能升级价格
async def get_equip_card_skill1_upgrade_price_service(db: AsyncSession, card_id: str) -> CCAssetBaseInfo:
    card = await get_equip_card_by_card_id(db, card_id)
    if card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
    if card.skill1_level is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    price = get_skill_upgrade_price(1, card.skill1_level)
    if price is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    return price

async def get_equip_card_skill2_upgrade_price_service(db: AsyncSession, card_id: str) -> CCAssetBaseInfo:
    card = await get_equip_card_by_card_id(db, card_id)
    if card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
    if card.skill2_level is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    price = get_skill_upgrade_price(2, card.skill2_level)
    if price is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    return price

async def get_equip_card_skill3_upgrade_price_service(db: AsyncSession, card_id: str) -> CCAssetBaseInfo:
    card = await get_equip_card_by_card_id(db, card_id)
    if card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
    if card.skill3_level is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    price = get_skill_upgrade_price(3, card.skill3_level)
    if price is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
    return price


def get_card_upgrade_price(card: UserEquipmentCard) -> List[CCAssetBaseInfo]:
    if card.level < 0 or card.level > 9:
        return []
    if card.level < 3:
        result = [CCAssetBaseInfo(ccasset_type=CCAssetType.STONE1, new_ccamount=10)]
    elif card.level < 6:
        result = [
            CCAssetBaseInfo(ccasset_type=CCAssetType.STONE1, new_ccamount=5),
            CCAssetBaseInfo(ccasset_type=CCAssetType.STONE2, new_ccamount=10)
        ]
    else:
        result = [
            CCAssetBaseInfo(ccasset_type=CCAssetType.STONE2, new_ccamount=5),
            CCAssetBaseInfo(ccasset_type=CCAssetType.STONE3, new_ccamount=10)
        ]
    return result

def get_skill_upgrade_price(skill: int, level: int) -> CCAssetBaseInfo | None:
    if level < 0 or level > 4:
        return None
    if skill == 1:
        price = CCAssetBaseInfo(ccasset_type=CCAssetType.STONE1, new_ccamount=level+1)
    elif skill == 2:
        price = CCAssetBaseInfo(ccasset_type=CCAssetType.STONE2, new_ccamount=level+1)
    else:
        price = CCAssetBaseInfo(ccasset_type=CCAssetType.STONE3, new_ccamount=level+1)
    return price

# 计算升级幅度
def sample_upgrade_amplitude(lucky_value: float, a: float = 8.0, p: float = 1.5) -> int:
    x = max(0.0, min(1.0, lucky_value / 100.0))
    alpha = 1.0 + a * (x ** p)
    beta = 1.0 + a * ((1.0 - x) ** p)
    # 简单 Beta 抽样（可用 numpy/scipy 或自写近似）
    y = random.betavariate(alpha, beta)  # Python 自带
    amp = max(1, min(100, math.ceil(100 * y)))
    return amp

# 卡牌材料升级
async def upgrade_equip_card_mat_service(
    db: AsyncSession,
    user_id: str,
    card_id: str
) -> EquipCardUpgradeResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.level < 0 or card.level > 9:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        prices = get_card_upgrade_price(card)
        new_ccassets = []
        for price in prices:
            new_amount = await consume_ccasset(db, price.ccasset_type, price.new_ccamount, user.id, f"升级卡牌 {card.equipment_def.name}")
            new_ccassets.append(CCAssetBaseInfo(ccasset_type=price.ccasset_type, new_ccamount=new_amount))
        card.level += 1
        card.multiplier += 0.001 * sample_upgrade_amplitude(card.lucky_value)
        db.add(card)
        card_info = equip_card_to_base_info(card)
        if card_info is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        return EquipCardUpgradeResponse(
            ccassets=new_ccassets,
            card=card_info
        )

# 卡牌融合升级
async def upgrade_equip_card_fusion_service(
    db: AsyncSession,
    card_id: str,
    fusion_card_id: str
) -> EquipCardBaseInfo:
    async with db.begin():
        if card_id == fusion_card_id:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.level < 0 or card.level > 9:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        fusion_card = await get_equip_card_by_card_id(db, fusion_card_id)
        if fusion_card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if fusion_card.level != 0 or card.equipment_def_id != fusion_card.equipment_def_id:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        await db.delete(fusion_card)
        card.level += 1
        card.multiplier += 0.001 * sample_upgrade_amplitude(card.lucky_value)
        db.add(card)
        card_info = equip_card_to_base_info(card)
        if card_info is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        return card_info

# 技能升级
async def upgrade_equip_card_skill1_service(
    db: AsyncSession,
    user_id: str,
    card_id: str
) -> EquipCardSkillUpgradeResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.skill1_level is None or card.level < 3 or card.skill1_level < 0 or card.skill1_level > 4:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        price = get_skill_upgrade_price(1, card.skill1_level)
        if price is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        new_amount = await consume_ccasset(db, price.ccasset_type, price.new_ccamount, user.id, f"升级卡牌 {card.equipment_def.name} 技能1")
        card.skill1_level += 1
        card.multiplier_skill1 += 0.001 * sample_upgrade_amplitude(card.lucky_value)
        db.add(card)
        card_info = equip_card_to_base_info(card)
        if card_info is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        return EquipCardSkillUpgradeResponse(
            ccasset=CCAssetBaseInfo(ccasset_type=price.ccasset_type, new_ccamount=new_amount),
            card=card_info
        )

async def upgrade_equip_card_skill2_service(
    db: AsyncSession,
    user_id: str,
    card_id: str
) -> EquipCardSkillUpgradeResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.skill2_level is None or card.level < 6 or card.skill2_level < 0 or card.skill2_level > 4:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        price = get_skill_upgrade_price(2, card.skill2_level)
        if price is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        new_amount = await consume_ccasset(db, price.ccasset_type, price.new_ccamount, user.id, f"升级卡牌 {card.equipment_def.name} 技能2")
        card.skill2_level += 1
        card.multiplier_skill2 += 0.001 * sample_upgrade_amplitude(card.lucky_value)
        db.add(card)
        card_info = equip_card_to_base_info(card)
        if card_info is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        return EquipCardSkillUpgradeResponse(
            ccasset=CCAssetBaseInfo(ccasset_type=price.ccasset_type, new_ccamount=new_amount),
            card=card_info
        )

async def upgrade_equip_card_skill3_service(
    db: AsyncSession,
    user_id: str,
    card_id: str
) -> EquipCardSkillUpgradeResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        card = await get_equip_card_by_card_id(db, card_id)
        if card is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
        if card.skill3_level is None or card.level < 10 or card.skill3_level < 0 or card.skill3_level > 4:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        price = get_skill_upgrade_price(3, card.skill3_level)
        if price is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.upgrade_failed")
        new_amount = await consume_ccasset(db, price.ccasset_type, price.new_ccamount, user.id, f"升级卡牌 {card.equipment_def.name} 技能3")
        card.skill3_level += 1
        card.multiplier_skill3 += 0.001 * sample_upgrade_amplitude(card.lucky_value)
        db.add(card)
        card_info = equip_card_to_base_info(card)
        if card_info is None:
            raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
        return EquipCardSkillUpgradeResponse(
            ccasset=CCAssetBaseInfo(ccasset_type=price.ccasset_type, new_ccamount=new_amount),
            card=card_info
        )