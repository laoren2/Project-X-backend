from typing import Optional, List, Any
from app.schemas.base import ORMBase
from enum import Enum


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
    version: str
    
    type_name: str
    tags: List[str]
    effect_def: dict[str, Any]