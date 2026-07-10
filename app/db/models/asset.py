import uuid
from sqlalchemy import (
    Column, String, Boolean, ForeignKey, DateTime, 
    func, UniqueConstraint, Integer, Float, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.asset import CPAssetType, AssetOperation
from app.schemas.common import SportType, CCAssetType
from app.db.base import Base
from sqlalchemy.orm import relationship
import hashlib
import json
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB



# cpassets的实时售价
class CPAssetPrice(Base):
    __tablename__ = "cpasset_price"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prop_def_id = Column(UUID(as_uuid=True), nullable=False)
    ccasset_type = Column(Enum(CCAssetType), nullable=False)
    price = Column(Integer, nullable=False)
    is_on_shelves = Column(Boolean, default=False, nullable=False)

    prop_def = relationship("CPAssetDef", primaryjoin="foreign(CPAssetPrice.prop_def_id)==CPAssetDef.id")
    
    __table_args__ = (
        UniqueConstraint("prop_def_id", name="uix_cpasset_price_prop_def_id"),
    )

# equipcards的实时售价
class EquipCardPrice(Base):
    __tablename__ = "equip_card_price"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    def_id = Column(UUID(as_uuid=True), nullable=False)
    ccasset_type = Column(Enum(CCAssetType), nullable=False)
    price = Column(Integer, nullable=False)
    is_on_shelves = Column(Boolean, default=False, nullable=False)

    card_def = relationship("EquipmentCardDef", primaryjoin="foreign(EquipCardPrice.def_id)==EquipmentCardDef.id")
    
    __table_args__ = (
        UniqueConstraint("def_id", name="uix_equip_card_price_def_id"),
    )

# 用户通用货币资产表 cc(common currency)
class CCUserAsset(Base):
    __tablename__ = "user_ccassets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    asset_type = Column(Enum(CCAssetType), nullable=False)
    balance = Column(Integer, default=0, nullable=False)
    can_recharge = Column(Boolean, default=False, nullable=False)
    can_withdraw = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(CCUserAsset.user_id)==User.id")

    __table_args__ = (
        UniqueConstraint("user_id", "asset_type", name="uix_user_ccasset"),
    )

# 通用货币资产变动记录
class CCAssetTransaction(Base):
    __tablename__ = "ccasset_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    asset_type = Column(Enum(CCAssetType), nullable=False)
    operation = Column(Enum(AssetOperation), nullable=False)
    change_amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(CCAssetTransaction.user_id)==User.id")


# 抽象道具定义父表
class CPAssetDef(Base):
    __tablename__ = "cp_asset_defs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(String, unique=True, index=True, nullable=False)
    prop_type = Column(Enum(CPAssetType), nullable=False)  # "registration_card", "team_card", ...
    sport_type = Column(Enum(SportType), nullable=False)   # 所属运动（所有 CPAsset 均归属某运动，用于商店/仓库按运动过滤）
    name_i18n = Column(JSONB, nullable=False)
    description_i18n = Column(JSONB, nullable=False)
    image_url = Column(String, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": prop_type,         # 通过该字段判断具体类型
        "polymorphic_identity": "base",      # 当前类是“基类”，默认类型名
    }

# 报名卡定义表
class CPRegistrationCardDef(CPAssetDef):
    __tablename__ = "cp_registration_card_defs"
    id = Column(UUID(as_uuid=True), ForeignKey("cp_asset_defs.id"), primary_key=True)
    is_team = Column(Boolean, nullable=False)
    premium = Column(Boolean, default=False, nullable=False)  # 高级赛道报名卡，配合 sport_type + is_team 唯一确定一张报名卡

    __mapper_args__ = {
        "polymorphic_identity": "registration_card",  # 当prop_type为"registration_card"时加载该子类
    }

# 创建队伍卡定义表
class CPTeamCardDef(CPAssetDef):
    __tablename__ = "cp_team_card_defs"
    id = Column(UUID(as_uuid=True), ForeignKey("cp_asset_defs.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "team_card",  # 当prop_type为"registration_card"时加载该子类
    }

# 创建路线卡定义表
class CPRouteCardDef(CPAssetDef):
    __tablename__ = "cp_route_card_defs"
    id = Column(UUID(as_uuid=True), ForeignKey("cp_asset_defs.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "route_card",  # 当prop_type为"route_card"时加载该子类
    }

# 用户通用道具资产表 cp(common prop)
class CPUserAsset(Base):
    __tablename__ = "user_cpassets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    prop_def_id = Column(UUID(as_uuid=True), nullable=False)
    balance = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(CPUserAsset.user_id)==User.id")
    prop_def = relationship("CPAssetDef", primaryjoin="foreign(CPUserAsset.prop_def_id)==CPAssetDef.id")

    __table_args__ = (
        UniqueConstraint("user_id", "prop_def_id", name="uix_user_cpasset"),
    )

# 用户通用道具资产变动记录
class CPAssetTransaction(Base):
    __tablename__ = "cpasset_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    prop_def_id = Column(UUID(as_uuid=True), nullable=False)
    operation = Column(Enum(AssetOperation), nullable=False)
    change_amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(CPAssetTransaction.user_id)==User.id")
    prop_def = relationship("CPAssetDef", primaryjoin="foreign(CPAssetTransaction.prop_def_id)==CPAssetDef.id")


# 装备卡定义表
class EquipmentCardDef(Base):
    __tablename__ = "equipment_card_defs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    def_id = Column(String, unique=True, index=True, nullable=False)
    #validation_token = Column(String, nullable=False)

    name_i18n = Column(JSONB, nullable=False)
    sport_type = Column(Enum(SportType), nullable=False)
    rarity = Column(String, nullable=False)
    description_i18n = Column(JSONB, nullable=False)
    skill1_description_i18n = Column(JSONB, nullable=True)
    skill2_description_i18n = Column(JSONB, nullable=True)
    skill3_description_i18n = Column(JSONB, nullable=True)
    image_url = Column(String, nullable=False)
    version = Column(String, nullable=False)

    #type_name = Column(String, nullable=False)           # 唯一的标识一个effect
    tags = Column(JSONB, nullable=False, default=list)   # 过滤标签，string数组
    effect_config = Column(JSONB, nullable=False)        # 包含基本使用方法/收益等配置

'''@event.listens_for(EquipmentCardDef, "before_insert")
def generate_validation_token(mapper, connection, target):
    if target.effect_config is not None:
        serialized = json.dumps(target.effect_config, sort_keys=True)
        target.validation_token = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    else:
        target.validation_token = ""

# 在更新时同步更新 validation_token，逻辑与 before_insert 保持一致
@event.listens_for(EquipmentCardDef, "before_update")
def update_validation_token(mapper, connection, target):
    if target.effect_config is not None:
        serialized = json.dumps(target.effect_config, sort_keys=True)
        target.validation_token = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    else:
        target.validation_token = ""'''

# 用户装备卡表（玩家持有的具体卡片）
class UserEquipmentCard(Base):
    __tablename__ = "user_equipment_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    equipment_def_id = Column(UUID(as_uuid=True), nullable=False)

    # 每个实例独有的动态属性
    level = Column(Integer, default=0, nullable=False)
    skill1_level = Column(Integer, nullable=True)
    skill2_level = Column(Integer, nullable=True)
    skill3_level = Column(Integer, nullable=True)
    lucky_value = Column(Float, nullable=False)
    multiplier = Column(Float, default=1, nullable=False)
    multiplier_skill1 = Column(Float, nullable=True)
    multiplier_skill2 = Column(Float, nullable=True)
    multiplier_skill3 = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(UserEquipmentCard.user_id)==User.id")
    equipment_def = relationship("EquipmentCardDef", primaryjoin="foreign(UserEquipmentCard.equipment_def_id)==EquipmentCardDef.id")

# 用户卡牌变动记录
class EquipCardTransaction(Base):
    __tablename__ = "equip_card_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    card_def_id = Column(UUID(as_uuid=True), nullable=False)
    operation = Column(Enum(AssetOperation), nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(EquipCardTransaction.user_id)==User.id")
    card = relationship("UserEquipmentCard", primaryjoin="foreign(EquipCardTransaction.card_id)==UserEquipmentCard.id")
    card_def = relationship("EquipmentCardDef", primaryjoin="foreign(EquipCardTransaction.card_def_id)==EquipmentCardDef.id")

# coupon 价格表
class CouponPrice(Base):
    __tablename__ = "coupon_prices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(String, unique=True, nullable=False)
    price = Column(Integer, nullable=False)
    gift_price = Column(Integer, nullable=True)    # 赠送的部分

# coupon 充值交易信息记录表
class CouponRechargeTransaction(Base):
    __tablename__ = "coupon_recharge_transaction"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    product_id = Column(String, nullable=False)
    original_transaction_id = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    type = Column(String, nullable=True)
    app_account_token = Column(String, nullable=True)
    price = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)