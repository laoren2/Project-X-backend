from typing import List, Any
from app.schemas.base import ORMBase
from enum import Enum
from pydantic import BaseModel


# 运动中实时预测名次 + 自我对比的开赛基线
class SplitProfileInfo(BaseModel):
    L: float                    # 路线总长（米）
    N: int                      # 里程桩数量
    splits: List[float]         # 各里程桩处的有效用时（N+1 个，splits[0]=0，splits[N]=有效完赛时间）

class PaceBaselineResponse(BaseModel):
    finish_times: List[float]   # 该路线/赛道按用时升序的完赛成绩（预测名次用）
    pb_profile: SplitProfileInfo | None = None   # 调用者个人最佳的 split profile（无则 null）


# 视频水印使用的完赛时快照。它固定“本次成绩写入排行榜之前”的 PB 与榜单，
# 之后重复生成视频时不再读取会变化的实时数据。
class PaceSnapshotResponse(BaseModel):
    version: int
    finish_times: List[float]
    pb_profile: SplitProfileInfo | None = None
    route_data: dict


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
            CCAssetType.STONE1: "升级材料1",
            CCAssetType.STONE2: "升级材料2",
            CCAssetType.STONE3: "升级材料3"
        }
        return names.get(self, "未知类型")

class SportType(str, Enum):
    running = "running"
    bike = "bike"

class PersonInfoResponse(ORMBase):
    user_id: str
    avatar_image_url: str
    nickname: str

class PersonInfoResponseList(BaseModel):
    users: List[PersonInfoResponse]

class CCAssetBaseInfo(BaseModel):
    ccasset_type: CCAssetType
    new_ccamount: int

class CCAssetRewardResponse(CCAssetBaseInfo):
    reward_amount: int

class CPAssetBaseInfo(ORMBase):
    asset_id: str
    name: str
    description: str
    image_url: str
    sport_type: SportType
    amount: int

class CPAssetCoverInfo(BaseModel):
    asset_id: str
    image_url: str

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

class CountryBBoxInfo(BaseModel):
    originLat: float
    originLng: float
    endLat: float
    endLng: float

class CountryBBoxConfig(BaseModel):
    country_code: str
    bbox: CountryBBoxInfo

class CountryBBoxResponse(BaseModel):
    configs: List[CountryBBoxConfig]
