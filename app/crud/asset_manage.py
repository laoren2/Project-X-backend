from sqlalchemy import select, func
from app.db.models.asset import (
    CCUserAsset, CCAssetTransaction, CPUserAsset, CPRouteCardDef,
    CPAssetTransaction, CPAssetDef, CPRegistrationCardDef, CPAssetPrice, CPTeamCardDef,
    EquipmentCardDef, EquipCardPrice, UserEquipmentCard, EquipCardTransaction, CouponPrice
)
from app.schemas.asset import AssetOperation, CPAssetType
from app.schemas.common import SportType, CCAssetType
from app.schemas.base import BizException
from app.core.errors import ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import random



# 消费cc资产
async def consume_ccasset(db: AsyncSession, asset_type: CCAssetType, amount: int, user_id: uuid.UUID, comment: str) -> int:
    asset = await get_or_create_user_ccasset(db, user_id, asset_type)
    if asset.balance < amount:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_enough", params={"asset_type": f"ccasset.{asset_type.value}"})
    new_balance = asset.balance - amount
    new_balance = await update_user_ccasset_balance(db, asset, new_balance)
    await create_ccasset_transaction(
        db, user_id, asset_type, AssetOperation.CONSUME, -amount, new_balance, description=comment
    )
    return new_balance

# 消费cp资产
async def consume_cpasset(db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID, amount: int, comment: str) -> int:
    asset = await get_or_create_user_cpasset(db, user_id, asset_id)
    if asset.balance < amount:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_enough", params={"asset_type": f"cpasset.{asset.prop_def.prop_type.value}"})
    new_balance = asset.balance - amount
    new_balance = await update_user_cpasset_balance(db, asset, new_balance)
    await create_cpasset_transaction(
        db, user_id, asset_id, AssetOperation.CONSUME, -amount, new_balance, description=comment
    )
    return new_balance

# 获得cc资产
async def reward_ccasset(db: AsyncSession, asset_type: CCAssetType, amount: int, user_id: uuid.UUID, comment: str, op: AssetOperation) -> int:
    asset = await get_or_create_user_ccasset(db, user_id, asset_type)
    new_balance = asset.balance + amount
    new_balance = await update_user_ccasset_balance(db, asset, new_balance)
    await create_ccasset_transaction(
        db, user_id, asset_type, op, amount, new_balance, description=comment
    )
    return new_balance

# 奖励cp资产
async def reward_cpasset(db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID, amount: int, comment: str, op: AssetOperation) -> int:
    asset = await get_or_create_user_cpasset(db, user_id, asset_id)
    new_balance = asset.balance + amount
    new_balance = await update_user_cpasset_balance(db, asset, new_balance)
    await create_cpasset_transaction(
        db, user_id, asset_id, op, amount, new_balance, description=comment
    )
    return new_balance

async def get_coupon_price(db: AsyncSession, product_id: str) -> CouponPrice | None:
    result = await db.execute(
        select(CouponPrice).where(
            CouponPrice.product_id == product_id
        )
    )
    return result.scalar_one_or_none()

async def get_coupon_prices_all(db: AsyncSession) -> List[CouponPrice]:
    result = await db.execute(
        select(CouponPrice)
    )
    return result.scalars().all()

async def get_cpasset_price_on_shelves(db: AsyncSession, asset_id: uuid.UUID) -> CPAssetPrice | None:
    result = await db.execute(
        select(CPAssetPrice).where(
            CPAssetPrice.prop_def_id == asset_id,
            CPAssetPrice.is_on_shelves == True
        )
    )
    return result.scalar_one_or_none()

# 查询报名卡的价格
async def get_register_card_price(db: AsyncSession, def_id: uuid.UUID) -> CPAssetPrice | None:
    result = await db.execute(
        select(CPAssetPrice).where(
            CPAssetPrice.prop_def_id == def_id
        )
    )
    return result.scalar_one_or_none()

async def create_user_ccasset(db: AsyncSession, user_id: uuid.UUID, asset_type: CCAssetType) -> CCUserAsset:
    can_recharge = False
    can_withdraw = False
    if asset_type == CCAssetType.COUPON:
        can_recharge = True
    elif asset_type == CCAssetType.VOUCHER:
        can_withdraw = True
    asset = CCUserAsset(
        user_id=user_id,
        asset_type=asset_type,
        can_recharge=can_recharge,
        can_withdraw=can_withdraw
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset

async def get_or_create_user_ccasset(db: AsyncSession, user_id: uuid.UUID, asset_type: CCAssetType) -> CCUserAsset:
    result = await db.execute(
        select(CCUserAsset)
        .where(CCUserAsset.user_id == user_id, CCUserAsset.asset_type == asset_type)
        .with_for_update()  # 加行级锁
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = await create_user_ccasset(db, user_id, asset_type)
    return asset

async def update_user_ccasset_balance(db: AsyncSession, asset: CCUserAsset, new_balance: int):
    asset.balance = new_balance
    db.add(asset)
    await db.flush()
    return asset.balance

async def create_ccasset_transaction(
    db: AsyncSession, user_id: uuid.UUID, asset_type: CCAssetType, operation: AssetOperation,
    change_amount: int, balance_after: int, description: str = None
):
    transaction = CCAssetTransaction(
        user_id=user_id,
        asset_type=asset_type,
        operation=operation,
        change_amount=change_amount,
        balance_after=balance_after,
        description=description
    )
    db.add(transaction)

async def get_cpasset_def_by_id(db: AsyncSession, asset_id: uuid.UUID) -> CPAssetDef | None:
    result = await db.execute(
        select(CPAssetDef).where(
            CPAssetDef.id == asset_id
        )
    )
    return result.scalar_one_or_none()

async def get_cpasset_def_by_asset_id(db: AsyncSession, asset_id: str) -> CPAssetDef | None:
    result = await db.execute(
        select(CPAssetDef).where(
            CPAssetDef.asset_id == asset_id
        )
    )
    return result.scalar_one_or_none()

async def query_cpasset_def_crud(
    db: AsyncSession,
    name: Optional[str],
    prop_type: Optional[str],
    page: int,
    size: int
) -> List[CPAssetDef]:
    query = select(CPAssetDef)
    if name:
        query = query.where(CPAssetDef.name.ilike(f"%{name}%"))
    if prop_type:
        try:
            query = query.where(CPAssetDef.prop_type == CPAssetType(prop_type))
        except ValueError:
            query = query.where(False)  # 不合法类型直接查空

    query = query.order_by(CPAssetDef.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()
    return items

async def get_registration_card_def(db: AsyncSession, sport_type: SportType, is_team: bool) -> CPRegistrationCardDef:
    result = await db.execute(
        select(CPRegistrationCardDef).where(
            CPRegistrationCardDef.sport_type == sport_type,
            CPRegistrationCardDef.is_team == is_team
        )
    )
    registration_card_def = result.scalar_one_or_none()
    if registration_card_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    return registration_card_def

async def get_team_card_def(db: AsyncSession, sport_type: SportType) -> CPTeamCardDef:
    result = await db.execute(
        select(CPTeamCardDef).where(
            CPTeamCardDef.sport_type == sport_type
        )
    )
    team_card_def = result.scalar_one_or_none()
    if team_card_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    return team_card_def

async def get_route_card_def(db: AsyncSession, sport_type: SportType) -> CPRouteCardDef | None:
    result = await db.execute(
        select(CPRouteCardDef).where(
            CPRouteCardDef.sport_type == sport_type
        )
    )
    return result.scalar_one_or_none()

async def get_cpassets_on_shelves_crud(db: AsyncSession) -> List[CPAssetPrice]:
    result = await db.execute(
        select(CPAssetPrice)
        .options(selectinload(CPAssetPrice.prop_def))
        .where(CPAssetPrice.is_on_shelves == True)
    )
    return result.scalars().all()

async def query_cpassets_in_shop_crud(
    db: AsyncSession,
    name: Optional[str],
    asset_id: Optional[str],
    is_on_shelves: Optional[str],
    page: int,
    size: int
) -> List[CPAssetPrice]:
    query = select(CPAssetPrice).options(
        selectinload(CPAssetPrice.prop_def)
    ).join(CPAssetPrice.prop_def)

    if name:
        query = query.where(CPAssetDef.name.ilike(f"%{name}%"))
    if asset_id:
        query = query.where(CPAssetDef.asset_id.ilike(f"%{asset_id}%"))
    if is_on_shelves is not None:
        query = query.where(CPAssetPrice.is_on_shelves == is_on_shelves)
    query = query.order_by(CPAssetPrice.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return result.scalars().all()

async def add_cpasset_to_shop_crud(db: AsyncSession, price: CPAssetPrice):
    db.add(price)
    await db.flush()

async def get_user_cpasset_all(db: AsyncSession, user_id: uuid.UUID) -> List[CPUserAsset]:
    result = await db.execute(
        select(CPUserAsset)
        .options(selectinload(CPUserAsset.prop_def))
        .where(CPUserAsset.user_id == user_id)
        .order_by(CPUserAsset.updated_at.desc())
    )
    return result.scalars().all()


# 暂不考虑极小概率情况下的高并发重复插入问题
async def create_user_cpasset(db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID) -> CPUserAsset:
    asset = CPUserAsset(
        user_id=user_id,
        prop_def_id=asset_id
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def get_or_create_user_cpasset(db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID) -> CPUserAsset:
    cpasset_def = await get_cpasset_def_by_id(db, asset_id)
    if cpasset_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    result = await db.execute(
        select(CPUserAsset)
        .options(selectinload(CPUserAsset.prop_def))
        .where(CPUserAsset.user_id == user_id, CPUserAsset.prop_def_id== asset_id)
        .with_for_update()  # 加行级锁
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = await create_user_cpasset(db, user_id, asset_id)
    return asset


async def update_user_cpasset_balance(db: AsyncSession, asset: CPUserAsset, new_balance: int):
    asset.balance = new_balance
    db.add(asset)
    await db.flush()
    return asset.balance

async def create_cpasset_transaction(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID, operation: AssetOperation,
    change_amount: int, balance_after: int, description: str = None
):
    transaction = CPAssetTransaction(
        user_id=user_id,
        prop_def_id=asset_id,
        operation=operation,
        change_amount=change_amount,
        balance_after=balance_after,
        description=description
    )
    db.add(transaction)

async def insert_cp_asset_def_and_child(db: AsyncSession, parent_data: dict, subclass, extra_fields: dict):
    # 合并所有字段
    child_data = {**parent_data, **extra_fields}
    child_instance = subclass(**child_data)
    db.add(child_instance)
    await db.flush()
    

async def query_equip_card_def_crud(
    db: AsyncSession,
    name: Optional[str],
    sport_type: Optional[SportType],
    page: int,
    size: int
) -> List[EquipmentCardDef]:
    query = select(EquipmentCardDef)
    if name:
        query = query.where(EquipmentCardDef.name.ilike(f"%{name}%"))
    if sport_type:
        try:
            query = query.where(EquipmentCardDef.sport_type == sport_type)
        except ValueError:
            query = query.where(False)  # 不合法类型直接查空

    query = query.order_by(EquipmentCardDef.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()
    return items

async def query_equip_cards_in_shop_crud(
    db: AsyncSession,
    name: Optional[str],
    card_id: Optional[str],
    is_on_shelves: Optional[str],
    page: int,
    size: int
) -> List[EquipCardPrice]:
    query = select(EquipCardPrice).options(
        selectinload(EquipCardPrice.card_def)
    ).join(EquipCardPrice.card_def)

    if name:
        query = query.where(EquipmentCardDef.name.ilike(f"%{name}%"))
    if card_id:
        query = query.where(EquipmentCardDef.def_id.ilike(f"%{card_id}%"))
    if is_on_shelves is not None:
        query = query.where(EquipCardPrice.is_on_shelves == is_on_shelves)
    query = query.order_by(EquipCardPrice.id.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return result.scalars().all()

async def get_equip_card_def_by_card_id(db: AsyncSession, card_id: str) -> EquipmentCardDef | None:
    result = await db.execute(
        select(EquipmentCardDef).where(
            EquipmentCardDef.def_id == card_id
        )
    )
    return result.scalar_one_or_none()

async def get_equip_card_by_card_id(db: AsyncSession, card_id: str) -> UserEquipmentCard | None:
    result = await db.execute(
        select(UserEquipmentCard)
        .options(
            selectinload(UserEquipmentCard.equipment_def)
        )
        .where(UserEquipmentCard.card_id == card_id)
    )
    return result.scalar_one_or_none()

async def get_equip_card_price_all_on_shelves(db: AsyncSession) -> List[EquipCardPrice]:
    result = await db.execute(
        select(EquipCardPrice)
        .options(selectinload(EquipCardPrice.card_def))
        .where(EquipCardPrice.is_on_shelves == True)
    )
    return result.scalars().all()

async def get_user_equip_cards_all(db: AsyncSession, user_id: uuid.UUID) -> List[UserEquipmentCard]:
    result = await db.execute(
        select(UserEquipmentCard)
        .options(selectinload(UserEquipmentCard.equipment_def))
        .where(UserEquipmentCard.user_id == user_id)
        .order_by(UserEquipmentCard.updated_at.desc())
    )
    return result.scalars().all()

async def get_equip_card_price_on_shelves(db: AsyncSession, card_id: uuid.UUID) -> EquipCardPrice | None:
    result = await db.execute(
        select(EquipCardPrice).where(
            EquipCardPrice.def_id == card_id,
            EquipCardPrice.is_on_shelves == True
        )
    )
    return result.scalar_one_or_none()

def generate_lucky_value(target_mean: float = 60.0, concentration: float = 25.0) -> float:
    """生成更集中且可控偏度的幸运值，使用 Beta 分布 (0 ~ 100)
    参数:
    - target_mean: 目标均值，默认 60(更贴近用户感受)
    - concentration: 集中度(alpha+beta)，越大分布越集中，默认 25
    """
    # 将目标均值与集中度映射为 Beta 分布参数
    m = max(0.01, min(0.99, target_mean / 100.0))
    c = max(2.0, concentration)  # 至少保证 alpha、beta > 1 时更平滑
    alpha = m * c
    beta = (1.0 - m) * c
    y = random.betavariate(alpha, beta)  # (0,1)
    # 映射到 (0,100)，并做轻微裁剪，避免极端 0/100
    value = y * 100.0
    if value <= 0:
        value = 0.1
    elif value >= 100:
        value = 99.9
    return value

async def create_user_equip_card(db: AsyncSession, user_id: uuid.UUID, card_def: EquipmentCardDef) -> UserEquipmentCard:
    card_id = f"equipcard_{uuid.uuid4()}"
    lucky_value = generate_lucky_value()
    card = UserEquipmentCard(
        card_id=card_id,
        user_id=user_id,
        equipment_def_id=card_def.id,
        level=0,
        lucky_value=lucky_value,
        multiplier=1
    )
    if card_def.skill1_description_i18n:
        card.skill1_level = 0
        card.multiplier_skill1 = 1
    if card_def.skill2_description_i18n:
        card.skill2_level = 0
        card.multiplier_skill2 = 1
    if card_def.skill3_description_i18n:
        card.skill3_level = 0
        card.multiplier_skill3 = 1
    db.add(card)
    await db.flush()
    await db.refresh(card)
    return card

async def create_equip_card_transaction(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    card_id: uuid.UUID,
    card_def_id: uuid.UUID,
    operation: AssetOperation,
    balance_after: int, 
    description: str = None
):
    transaction = EquipCardTransaction(
        user_id=user_id,
        card_id=card_id,
        card_def_id=card_def_id,
        operation=operation,
        balance_after=balance_after,
        description=description
    )
    db.add(transaction)