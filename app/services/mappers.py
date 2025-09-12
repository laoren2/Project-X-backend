from app.db.models.asset import UserEquipmentCard
from app.schemas.common import EquipCardBaseInfo
from app.schemas.base import BizException
from app.core.errors import ErrorCode


def equip_card_to_base_info(card: UserEquipmentCard) -> EquipCardBaseInfo | None:
    card_def = card.equipment_def
    if card_def is None:
        return None
    return EquipCardBaseInfo(
        card_id=card.card_id,
        def_id=card_def.def_id,
        name=card_def.name,
        sport_type=card_def.sport_type,
        level=card.level,
        levelSkill1=card.skill1_level,
        levelSkill2=card.skill2_level,
        levelSkill3=card.skill3_level,
        image_url=card_def.image_url,
        lucky=card.lucky_value,
        rarity=card_def.rarity,
        description=card_def.description,
        description_skill1=card_def.skill1_description,
        description_skill2=card_def.skill2_description,
        description_skill3=card_def.skill3_description,
        multiplier=card.multiplier,
        multiplier_skill1=card.multiplier_skill1,
        multiplier_skill2=card.multiplier_skill2,
        multiplier_skill3=card.multiplier_skill3,
        version=card_def.version,
        type_name=card_def.type_name,
        tags=card_def.tags,
        effect_def=card_def.effect_config
    )


