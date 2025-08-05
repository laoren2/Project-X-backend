from typing import Optional, List
from app.schemas.base import ORMBase
from app.schemas.common import CPAssetBaseInfo
from enum import Enum
from fastapi import Form


class CCAssetType(str, Enum):
    COIN = "coin"        # 金币
    COUPON = "coupon"    # 点券
    VOUCHER = "voucher"  # 金券
    #DIAMOND = "diamond"  # 钻石

    def display_name(self) -> str:
        names = {
            CCAssetType.COIN: "金币",
            CCAssetType.COUPON: "点券",
            CCAssetType.VOUCHER: "金券"
            #CCAssetType.DIAMOND: "钻石",
        }
        return names.get(self, "未知类型")

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

class EquipmentCardType(str, Enum):
    WATER = "water"
    FIRE = "fire"

class CCAssetsResponse(ORMBase):
    coin_amount: int
    coupon_amount: int
    voucher_amount: int

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

class CPAssetShopInternalInfo(CPAssetShopInfo):
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
    name: str
    description: str
    image_url: str

class CPAssetDefResponse(ORMBase):
    defs: List[CPAssetDefInfo]

class CPAssetBuyRequest(ORMBase):
    cpasset_id: str
    cpamount: int

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

class CCAssetRewardRequest(ORMBase):
    user_id: str
    ccasset_type: CCAssetType
    amount: int