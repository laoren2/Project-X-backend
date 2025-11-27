from typing import Optional, List, Any
from app.schemas.base import ORMBase
from enum import Enum
from pydantic import BaseModel


class CCAssetType(str, Enum):
    COIN = "coin"        # 金币
    COUPON = "coupon"    # 点券
    VOUCHER = "voucher"  # 金券
    STONE1 = "stone1"
    STONE2 = "stone2"
    STONE3 = "stone3"

    def display_name(self) -> str:
        names = {
            CCAssetType.COIN: "金币",
            CCAssetType.COUPON: "点券",
            CCAssetType.VOUCHER: "金券",
            CCAssetType.STONE1: "升级石1",
            CCAssetType.STONE2: "升级石2",
            CCAssetType.STONE3: "升级石3"
        }
        return names.get(self, "未知类型")

class SportType(str, Enum):
    running = "running"
    bike = "bike"

class PersonInfoResponse(ORMBase):
    user_id: str
    avatar_image_url: str
    nickname: str

class CPAssetBaseInfo(ORMBase):
    asset_id: str
    name: str
    description: str
    image_url: str
    amount: int

class EquipCardBaseInfo(ORMBase):
    card_id: str
    def_id: str
    name: str
    sport_type: SportType
    level: int                      # 1-10级
    levelSkill1: int | None         # 0-5级，level=3时解锁
    levelSkill2: int | None         # 0-5级，level=6时解锁
    levelSkill3: int | None         # 0-5级，level=10时解锁
    image_url: str
    lucky: float
    rarity: str
    description: str
    description_skill1: str | None
    description_skill2: str | None
    description_skill3: str | None
    multiplier: float
    multiplier_skill1: float | None
    multiplier_skill2: float | None
    multiplier_skill3: float | None
    version: str
    
    #type_name: str
    tags: List[str]
    effect_def: dict[str, Any]