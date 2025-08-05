from typing import Optional, List
from app.schemas.base import ORMBase



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