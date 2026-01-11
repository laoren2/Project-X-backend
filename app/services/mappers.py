from app.db.models.asset import UserEquipmentCard
from app.schemas.common import EquipCardBaseInfo
from app.schemas.base import BizException, Language, pick_i18n_text
from app.core.errors import ErrorCode


def equip_card_to_base_info(card: UserEquipmentCard, lang: Language) -> EquipCardBaseInfo | None:
    card_def = card.equipment_def
    if card_def is None:
        return None
    return EquipCardBaseInfo(
        card_id=card.card_id,
        def_id=card_def.def_id,
        name=pick_i18n_text(card_def.name_i18n, lang),
        sport_type=card_def.sport_type,
        level=card.level,
        levelSkill1=card.skill1_level,
        levelSkill2=card.skill2_level,
        levelSkill3=card.skill3_level,
        image_url=card_def.image_url,
        lucky=card.lucky_value,
        rarity=card_def.rarity,
        description=pick_i18n_text(card_def.description_i18n, lang),
        description_skill1=pick_i18n_text(card_def.skill1_description_i18n, lang) if card_def.skill1_description_i18n else None,
        description_skill2=pick_i18n_text(card_def.skill2_description_i18n, lang) if card_def.skill2_description_i18n else None,
        description_skill3=pick_i18n_text(card_def.skill3_description_i18n, lang) if card_def.skill3_description_i18n else None,
        multiplier=card.multiplier,
        multiplier_skill1=card.multiplier_skill1,
        multiplier_skill2=card.multiplier_skill2,
        multiplier_skill3=card.multiplier_skill3,
        version=card_def.version,
        #type_name=card_def.type_name,
        tags=card_def.tags,
        effect_def=card_def.effect_config
    )


