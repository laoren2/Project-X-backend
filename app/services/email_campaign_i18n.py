from dataclasses import dataclass

from app.schemas.base import Language


# Campaign recipient records store one of these language values at creation time.
@dataclass(frozen=True)
class VideoWatermarkEmailCopy:
    subject: str
    hero_alt: str
    title: str
    description: str
    feature_1: str
    feature_2: str
    feature_3: str
    cta: str
    marketing_notice: str
    unsubscribe: str
    plain_text: str
    unsubscribe_title: str
    unsubscribe_message: str

    @classmethod
    def from_mapping(cls, copy: dict[str, str]) -> "VideoWatermarkEmailCopy":
        return cls(**copy)


VIDEO_WATERMARK_EMAIL_COPY: dict[Language, VideoWatermarkEmailCopy] = {
    Language.zh_hans: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】给你的运动视频，加上专属数据水印", "hero_alt": "骑行与跑步视频水印功能",
        "title": "给你的运动视频，加上专属数据水印",
        "description": "现在，你可以把运动轨迹、速度、距离、心率，甚至是赛道排名等数据，以精致的视频水印叠加到骑行或跑步视频中，让每一次坚持都更值得分享。",
        "feature_1": "从相册选择视频，自动匹配本次运动数据", "feature_2": "选择想要叠加的水印数据并自由编辑", "feature_3": "一键导出属于你的运动高光时刻",
        "cta": "立即体验", "marketing_notice": "这是一封 Movmov 产品功能宣传邮件。", "unsubscribe": "取消订阅产品邮件",
        "plain_text": "Movmov 推出了视频数据水印功能。现在就能将轨迹、速度、距离、心率和赛道排名等数据叠加到你的运动视频中。请在 Movmov App 内体验。",
        "unsubscribe_title": "已取消订阅", "unsubscribe_message": "你将不再收到 Movmov 的产品宣传邮件。",
    }),
    Language.zh_hant: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】為你的運動影片，加上專屬數據浮水印", "hero_alt": "騎行與跑步影片浮水印功能",
        "title": "為你的運動影片，加上專屬數據浮水印",
        "description": "現在，你可以把運動軌跡、速度、距離、心率，甚至賽道排名等資料，以精緻的影片浮水印疊加到騎行或跑步影片中，讓每一次堅持都更值得分享。",
        "feature_1": "從相簿選擇影片，自動配對本次運動資料", "feature_2": "選擇想疊加的浮水印資料並自由編輯", "feature_3": "一鍵匯出屬於你的運動高光時刻",
        "cta": "立即體驗", "marketing_notice": "這是一封 Movmov 產品功能宣傳郵件。", "unsubscribe": "取消訂閱產品郵件",
        "plain_text": "Movmov 推出了影片數據浮水印功能。現在就能將軌跡、速度、距離、心率和賽道排名等資料疊加到你的運動影片中。請在 Movmov App 內體驗。",
        "unsubscribe_title": "已取消訂閱", "unsubscribe_message": "你將不再收到 Movmov 的產品宣傳郵件。",
    }),
    Language.en: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】Add your workout data to every video", "hero_alt": "Cycling and running video watermark feature",
        "title": "Add your workout data to every video",
        "description": "Turn your route, speed, distance, heart rate, and even race ranking into a polished overlay for your cycling or running videos—so every effort is worth sharing.",
        "feature_1": "Choose a video from your library and match it with the workout", "feature_2": "Pick the data to overlay and edit it your way", "feature_3": "Export your workout highlight in one tap",
        "cta": "Try it now", "marketing_notice": "This is a Movmov product feature announcement.", "unsubscribe": "Unsubscribe from product emails",
        "plain_text": "Movmov has introduced video data watermarks. Add your route, speed, distance, heart rate, and race ranking to your workout videos in the Movmov app.",
        "unsubscribe_title": "You have unsubscribed", "unsubscribe_message": "You will no longer receive Movmov product announcement emails.",
    }),
    Language.ko: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】운동 영상에 나만의 데이터 워터마크를 더해 보세요", "hero_alt": "사이클링 및 러닝 영상 워터마크 기능",
        "title": "운동 영상에 나만의 데이터 워터마크를 더해 보세요",
        "description": "운동 경로, 속도, 거리, 심박수, 레이스 순위까지 세련된 영상 워터마크로 사이클링과 러닝 영상에 더해 보세요. 매 순간의 노력이 더욱 빛납니다.",
        "feature_1": "앨범에서 영상을 선택하면 운동 데이터를 자동으로 연결합니다", "feature_2": "원하는 워터마크 데이터를 골라 자유롭게 편집합니다", "feature_3": "나만의 운동 하이라이트를 한 번에 내보냅니다",
        "cta": "지금 체험하기", "marketing_notice": "Movmov의 새로운 기능을 알리는 이메일입니다.", "unsubscribe": "제품 이메일 수신 거부",
        "plain_text": "Movmov에 영상 데이터 워터마크 기능이 추가되었습니다. Movmov 앱에서 경로, 속도, 거리, 심박수, 레이스 순위를 운동 영상에 더해 보세요.",
        "unsubscribe_title": "구독이 취소되었습니다", "unsubscribe_message": "Movmov 제품 안내 이메일을 더 이상 받지 않습니다.",
    }),
    Language.ja: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】運動動画にあなた専用のデータ透かしを", "hero_alt": "サイクリングとランニング動画の透かし機能",
        "title": "運動動画にあなた専用のデータ透かしを",
        "description": "走行ルート、速度、距離、心拍数、レース順位まで。サイクリングやランニングの動画に洗練されたデータ透かしとして重ね、頑張った瞬間をもっと共有しやすくできます。",
        "feature_1": "アルバムから動画を選ぶと、今回の運動データを自動で照合", "feature_2": "重ねるデータを選び、自由に編集", "feature_3": "あなたの運動ハイライトをワンタップで書き出し",
        "cta": "今すぐ試す", "marketing_notice": "Movmov の新機能をお知らせするメールです。", "unsubscribe": "製品メールの配信を停止",
        "plain_text": "Movmov に動画データ透かし機能が追加されました。アプリでルート、速度、距離、心拍数、レース順位を運動動画に重ねてみましょう。",
        "unsubscribe_title": "配信を停止しました", "unsubscribe_message": "Movmov の製品案内メールは今後届かなくなります。",
    }),
    Language.fr: VideoWatermarkEmailCopy.from_mapping({
        "subject": "【Movmov】Ajoutez vos données sportives à chaque vidéo", "hero_alt": "Fonction de filigrane pour vidéos de vélo et de course",
        "title": "Ajoutez vos données sportives à chaque vidéo",
        "description": "Ajoutez votre itinéraire, votre vitesse, votre distance, votre fréquence cardiaque et même votre classement à vos vidéos de vélo ou de course grâce à un élégant filigrane.",
        "feature_1": "Choisissez une vidéo dans votre photothèque et associez-la à votre activité", "feature_2": "Sélectionnez les données à afficher et personnalisez-les librement", "feature_3": "Exportez votre meilleur moment sportif en un geste",
        "cta": "Essayer maintenant", "marketing_notice": "Cet e-mail présente une nouvelle fonctionnalité de Movmov.", "unsubscribe": "Se désabonner des e-mails produit",
        "plain_text": "Movmov propose désormais des filigranes de données pour vos vidéos. Ajoutez votre itinéraire, votre vitesse, votre distance, votre fréquence cardiaque et votre classement à vos vidéos dans l’app Movmov.",
        "unsubscribe_title": "Vous êtes désabonné(e)", "unsubscribe_message": "Vous ne recevrez plus les e-mails d’annonce produit de Movmov.",
    }),
}


def get_video_watermark_email_copy(language: Language) -> VideoWatermarkEmailCopy:
    return VIDEO_WATERMARK_EMAIL_COPY.get(language, VIDEO_WATERMARK_EMAIL_COPY[Language.en])
