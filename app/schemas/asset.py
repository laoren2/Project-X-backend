from typing import Optional, List, Any
from app.schemas.base import ORMBase
from app.schemas.common import CPAssetBaseInfo, EquipCardBaseInfo, SportType, CCAssetType, CCAssetBaseInfo
from app.core.storage import build_resource_url
from enum import Enum
from fastapi import Form
from pydantic import BaseModel, field_validator


class CPAssetType(str, Enum):
    registration_card = "registration_card"     # 报名卡
    team_card = "team_card"                     # 创建队伍卡

    def display_name(self) -> str:
        names = {
            CPAssetType.registration_card: "报名卡",
            CPAssetType.team_card: "组队卡"
        }
        return names.get(self, "未知类型")

class AssetOperation(str, Enum):
    RECHARGE = "recharge"   # 充值
    CONSUME = "consume"     # 消费
    TRANSFER = "transfer"   # 转账
    REWARD = "reward"       # 奖励
    WITHDRAW = "withdraw"   # 提现
    REFUND = "refund"       # 退回
    DESTROY = "destroy"     # 销毁
    UPGRADE = "upgrade"     # 升级

class CCAssetsResponse(ORMBase):
    coin_amount: int
    coupon_amount: int
    voucher_amount: int
    stone1_amount: int
    stone2_amount: int
    stone3_amount: int

class CPAssetResponse(ORMBase):
    asset_id: str
    new_balance: int

class CPAssetsResponse(ORMBase):
    assets: List[CPAssetBaseInfo]

class CPAssetShopInfo(ORMBase):
    asset_id: str
    name: str
    description: str
    image_url: str
    ccasset_type: CCAssetType
    price: int

class CPAssetsShopResponse(ORMBase):
    assets: List[CPAssetShopInfo]

class CPAssetShopInternalInfo(BaseModel):
    asset_id: str
    name: dict[str, Any]
    description: dict[str, Any]
    image_url: str
    ccasset_type: CCAssetType
    price: int
    is_on_shelves: bool

class CPAssetsShopInternalResponse(ORMBase):
    assets: List[CPAssetShopInternalInfo]

class CPAssetShopInfoCreateRequest(ORMBase):
    asset_id: str
    ccasset_type: CCAssetType
    price: int
    is_on_shelves: bool

class CPAssetShopInfoUpdateRequest(ORMBase):
    asset_id: str
    price: int
    is_on_shelves: bool

class CPAssetDefInfo(ORMBase):
    asset_id: str
    cpasset_type: CPAssetType
    name: dict[str, Any]
    description: dict[str, Any]
    image_url: str

class CPAssetDefResponse(ORMBase):
    defs: List[CPAssetDefInfo]

class CPAssetBuyRequest(ORMBase):
    cpasset_id: str
    cpamount: int

class CC_CC_BuyRequest(ORMBase):
    buy: CCAssetType
    amount: int
    use: CCAssetType

class CC_CC_PurchaseResultResponse(ORMBase):
    decrease_type: CCAssetType
    decrease_amount: int
    increase_type: CCAssetType
    increase_amount: int

class CC_CP_PurchaseResultResponse(ORMBase):
    ccasset_type: CCAssetType
    new_ccamount: int
    cpasset_id: str
    new_cpamount: int

class CC_ECARD_PurchaseResultResponse(BaseModel):
    ccasset_type: CCAssetType
    new_ccamount: int
    card: EquipCardBaseInfo

class CPAssetDefCreateForm(ORMBase):
    prop_type: str
    name: str
    description: str
    extra_fields: str  # 后续手动json.loads

    @classmethod
    def as_form(
        cls,
        prop_type: str = Form(...),
        name: str = Form(...),
        description: str = Form(...),
        extra_fields: str = Form(...)
    ):
        return cls(
            prop_type=prop_type,
            name=name,
            description=description,
            extra_fields=extra_fields
        )

class CPAssetDefUpdateForm(BaseModel):
    asset_id: str
    name: str
    description: str

    @classmethod
    def as_form(
        cls,
        asset_id: str = Form(...),
        name: str = Form(...),
        description: str = Form(...)
    ):
        return cls(
            asset_id=asset_id,
            name=name,
            description=description
        )

class CCAssetRewardRequest(ORMBase):
    user_id: str
    ccasset_type: CCAssetType
    amount: int

class EquipCardDefCreateForm(ORMBase):
    def_id: str
    name: str
    sport_type: SportType
    rarity: str
    description: str
    skill1_description: str | None
    skill2_description: str | None
    skill3_description: str | None
    version: str
    tags: str           # 后续手动json.loads
    effect_config: str  # 后续手动json.loads

    @classmethod
    def as_form(
        cls,
        def_id: str = Form(...),
        name: str = Form(...),
        sport_type: SportType = Form(...),
        rarity: str = Form(...),
        description: str = Form(...),
        skill1_description: str | None = Form(None),
        skill2_description: str | None = Form(None),
        skill3_description: str | None = Form(None),
        version: str = Form(...),
        tags: str = Form("[]"),
        effect_config: str = Form(...)
    ):
        return cls(
            def_id=def_id,
            name=name,
            sport_type=sport_type,
            rarity=rarity,
            description=description,
            skill1_description=skill1_description,
            skill2_description=skill2_description,
            skill3_description=skill3_description,
            version=version,
            tags=tags,
            effect_config=effect_config
        )

class EquipCardDefUpdateForm(BaseModel):
    def_id: str
    name: str
    description: str
    skill1_description: str | None
    skill2_description: str | None
    skill3_description: str | None
    version: str

    @classmethod
    def as_form(
        cls,
        def_id: str = Form(...),
        name: str = Form(...),
        description: str = Form(...),
        skill1_description: str | None = Form(None),
        skill2_description: str | None = Form(None),
        skill3_description: str | None = Form(None),
        version: str = Form(...)
    ):
        return cls(
            def_id=def_id,
            name=name,
            description=description,
            skill1_description=skill1_description,
            skill2_description=skill2_description,
            skill3_description=skill3_description,
            version=version
        )

class EquipCardDefInfo(ORMBase):
    def_id: str
    name_i18n: dict[str, Any]
    image_url: str
    sport_type: SportType
    rarity: str
    description_i18n: dict[str, Any]
    skill1_description_i18n: dict[str, Any] | None
    skill2_description_i18n: dict[str, Any] | None
    skill3_description_i18n: dict[str, Any] | None
    version: str
    #type_name: str
    tags: List[str]
    effect_config: dict[str, Any]

    @field_validator("image_url", mode="after")
    def build_avatar_url(cls, v):
        if not v:
            return v
        return build_resource_url(v)

class EquipCardDefResponse(BaseModel):
    defs: List[EquipCardDefInfo]

class EquipCardShopInfoCreateRequest(ORMBase):
    card_def_id: str
    ccasset_type: CCAssetType
    price: int
    is_on_shelves: bool

class EquipCardShopInfo(BaseModel):
    def_id: str
    name: str
    image_url: str
    sport_type: SportType
    rarity: str
    description: str
    skill1_description: str | None
    skill2_description: str | None
    skill3_description: str | None
    version: str
    effect_config: dict[str, Any]

    ccasset_type: CCAssetType
    price: int

class EquipCardShopResponse(BaseModel):
    cards: List[EquipCardShopInfo]

class EquipCardShopInternalInfo(BaseModel):
    def_id: str
    name: dict[str, Any]
    image_url: str
    sport_type: SportType
    rarity: str
    description: dict[str, Any]
    skill1_description: dict[str, Any] | None
    skill2_description: dict[str, Any] | None
    skill3_description: dict[str, Any] | None
    version: str
    effect_config: dict[str, Any]

    ccasset_type: CCAssetType
    price: int
    is_on_shelves: bool

class EquipCardShopInternalResponse(BaseModel):
    cards: List[EquipCardShopInternalInfo]

class EquipCardsResponse(BaseModel):
    cards: List[EquipCardBaseInfo]

class EquipCardUpgradeResponse(BaseModel):
    ccassets: List[CCAssetBaseInfo]
    card: EquipCardBaseInfo

class EquipCardSkillUpgradeResponse(BaseModel):
    ccasset: CCAssetBaseInfo
    card: EquipCardBaseInfo

class EquipCardUpgradePriceInfo(BaseModel):
    prices: List[CCAssetBaseInfo]

class AssetRewardsResponse(BaseModel):
    ccassets: List[CCAssetBaseInfo]
    cpassets: List[CPAssetResponse]
    equip_cards: List[EquipCardBaseInfo]

class SignInItemInfo(BaseModel):
    date: str                       # yyyy-MM-dd
    is_today: bool                  # 统一时区为 HK （ UTC+8 ）
    ccasset_type: CCAssetType       # 非订阅奖励
    ccasset_reward: int             # 非订阅奖励
    ccasset_type_vip: CCAssetType   # 订阅奖励
    ccasset_reward_vip: int         # 订阅奖励

class SignInStatusResponse(BaseModel):
    today_signed: bool              # 今天是否已签到
    today_signed_vip: bool          # 今天是否已签到（会员）
    #continuous_days: int            # 连续签到天数
    items: List[SignInItemInfo]

class SignInRewardResponse(CCAssetBaseInfo):
    date: str

class DailyTaskRewardResponse(BaseModel):
    ccasset_type: CCAssetType | None
    ccasset_amount: int | None
    cpasset_id: str | None
    cpasset_amount: int | None

class CouponShopInfo(BaseModel):
    product_id: str
    coupon: int
    coupon_gift: int | None

class CouponShopResponse(BaseModel):
    coupons: List[CouponShopInfo]