# 响应错误码

class ErrorCode:
    # 成功
    SUCCESS = 0

    # 通用
    IMAGE_UPLOAD_OVERSIZE = 1001

    # 用户相关
    USER_NOT_FOUND = 2001
    USER_FOLLOW_SELF = 2002
    USER_FOLLOW_REPEAT = 2003
    USER_INFO_ERROR = 2004
    USER_BANNED = 2005
    USER_DELETED = 2006    

    # 身份验证
    SMS_VERIFY_FAILED = 3001
    TOKEN_INVALID = 3002
    TOKEN_EXPIRED = 3003
    NO_PERMISSION = 3004
    REALNAME_FAILED = 3005
    PHONE_NUMBER_ERROR = 3006
    APPLE_ID_ERROR = 3007
    EMAIL_VERIFY_FAILED = 3008
    EMAIL_ERROR = 3009
    IDENTITY_LINK_REQUIRED = 3010
    GOOGLE_ID_ERROR = 3011

    # 业务逻辑
    SEASON_ERROR = 4001
    REGION_ERROR = 4002
    EVENT_ERROR = 4003
    TRACK_ERROR = 4004
    RECORD_ERROR = 4005
    TEAM_ERROR = 4006
    ASSET_ERROR = 4007
    LEADERBOARD_ERROR = 4008
    MAIL_NOT_FOUND = 4009
    IAP_ERROR = 4010
    FEEDBACK_COMMIT_ERROR = 4011
    REWARD_CLAIM_FAILED = 4012
    ROUTE_NOT_FOUND = 4013
    ROUTE_CREATE_FAILED = 4014
    ROUTE_UPDATE_FAILED = 4015
    ROUTE_APPLY_ERROR = 4016
    EMAIL_CAMPAIGN_NOT_FOUND = 4017
    EMAIL_CAMPAIGN_STATE_ERROR = 4018

    # 第三方服务
    SMS_SERVICE_ERROR = 5001
    EMAIL_SERVICE_ERROR = 5002
    APPLE_SERVICE_ERROR = 5003
    OSS_SERVICE_ERROR = 5004
    GOOGLE_SERVICE_ERROR = 5005

    # 后台管理业务逻辑专属
    TABLE_NOT_FOUND = 6001
    PROPERTY_ERROR = 6002
    JSON_DECODE_ERROR = 6003
    FEEDBACK_MAIL_NOT_FOUND = 6004
    FILE_NOT_FOUND = 6005

    # 系统
    DATABASE_ERROR = 9001
    UNKNOWN_ERROR = 9999

# 命名方式 - object.reason.scene
ERROR_MESSAGES = {
# 通用
    "image.over_size": {
        "zh-Hans": "上传图片体积过大，请重试",
        "zh-Hant": "上傳圖片體積過大，請重識",
        "en": "Image is oversize, please try again.",
        "ko": "이미지 용량이 너무 큽니다. 다시 시도해주세요",
        "ja": "画像サイズが大きすぎます。再試行してください",
        "fr": "L'image est trop volumineuse, veuillez réessayer."
    },
    "email_campaign.not_found": {
        "zh-Hans": "邮件群发活动不存在",
        "zh-Hant": "郵件群發活動不存在",
        "en": "Email campaign not found",
        "ko": "이메일 캠페인을 찾을 수 없습니다",
        "ja": "メールキャンペーンが見つかりません",
        "fr": "Campagne e-mail introuvable"
    },
    "email_campaign.invalid_state": {
        "zh-Hans": "邮件群发活动当前状态不能开始发送",
        "zh-Hant": "郵件群發活動目前狀態無法開始發送",
        "en": "The email campaign cannot be started in its current state",
        "ko": "현재 상태에서는 이메일 캠페인을 시작할 수 없습니다",
        "ja": "現在の状態ではメールキャンペーンを開始できません",
        "fr": "La campagne e-mail ne peut pas démarrer dans son état actuel"
    },
# 用户
    "user.not_found": {
        "zh-Hans": "用户不存在",
        "zh-Hant": "用戶不存在",
        "en": "User not exist",
        "ko": "사용자가 존재하지 않습니다",
        "ja": "ユーザーが存在しません",
        "fr": "L'utilisateur n'existe pas"
    },
    "user.info_error": {
        "zh-Hans": "用户信息错误",
        "zh-Hant": "用戶信息錯誤",
        "en": "User info error",
        "ko": "사용자 정보 오류",
        "ja": "ユーザー情報エラー",
        "fr": "Erreur d'informations utilisateur"
    },
    "user.follow_self": {
        "zh-Hans": "不能关注自己",
        "zh-Hant": "不能關注自己",
        "en": "Cannot follow yourself",
        "ko": "자기 자신을 팔로우할 수 없습니다",
        "ja": "自分自身をフォローできません",
        "fr": "Vous ne pouvez pas vous suivre vous-même"
    },
    "user.cancel_follow_self": {
        "zh-Hans": "不能取消关注自己",
        "zh-Hant": "不能取消關注自己",
        "en": "Cannot cancel follow yourself",
        "ko": "자기 자신을 팔로우 취소할 수 없습니다",
        "ja": "自分自身のフォローは解除できません",
        "fr": "Vous ne pouvez pas vous désabonner de vous-même"
    },
    "user.repeat_follow": {
        "zh-Hans": "请勿重复关注",
        "zh-Hant": "請勿重複關注",
        "en": "Do not follow repeatedly",
        "ko": "중복으로 팔로우할 수 없습니다",
        "ja": "重複してフォローできません",
        "fr": "Ne suivez pas en double"
    },
    "user.banned": {
        "zh-Hans": "账号已封禁\n剩余时间：{remaining}",
        "zh-Hant": "帳號已封禁\n剩餘時間：{remaining}",
        "en": "Account has been banned\nremaining time: {remaining}",
        "ko": "계정이 정지되었습니다\n남은 시간: {remaining}",
        "ja": "アカウントが停止されています\n残り時間：{remaining}",
        "fr": "Le compte a été banni\nTemps restant : {remaining}"
    },
    "user.deleted": {
        "zh-Hans": "账号已注销",
        "zh-Hant": "帳號已註銷",
        "en": "Account has been deleted",
        "ko": "계정이 삭제되었습니다",
        "ja": "アカウントは削除されています",
        "fr": "Le compte a été supprimé"
    },
# 身份校验
    "identity.verify_failed.test_account": {
        "zh-Hans": "账号信息错误",
        "zh-Hant": "帳號信息錯誤",
        "en": "Account info error",
        "ko": "계정 정보 오류",
        "ja": "アカウント情報エラー",
        "fr": "Erreur d'informations du compte"
    },
    "identity.verify_failed.sms": {
        "zh-Hans": "验证码错误",
        "zh-Hant": "驗證碼錯誤",
        "en": "Verification code error",
        "ko": "인증 코드가 올바르지 않습니다",
        "ja": "認証コードが正しくありません",
        "fr": "Code de vérification incorrect"
    },
    "identity.verify_failed.apple": {
        "zh-Hans": "Apple 登录校验失败",
        "zh-Hant": "Apple 登錄校驗失敗",
        "en": "Apple login verification failed",
        "ko": "Apple 로그인 인증 실패",
        "ja": "Appleログイン認証に失敗しました",
        "fr": "Échec de la vérification de connexion Apple"
    },
    "identity.verify_failed.google": {
        "zh-Hans": "Google 登录校验失败",
        "zh-Hant": "Google 登錄校驗失敗",
        "en": "Google sign-in verification failed",
        "ko": "Google 로그인 인증에 실패했습니다",
        "ja": "Google ログインの検証に失敗しました",
        "fr": "Échec de la vérification de connexion Google"
    },
    "identity.account_exists.link_required": {
        "zh-Hans": "该邮箱已关联现有账号，请先使用原登录方式登录后再绑定此账号",
        "zh-Hant": "該郵箱已關聯現有帳號，請先使用原登入方式登入後再綁定此帳號",
        "en": "This email is already linked to an account. Sign in with the original method, then link this account.",
        "ko": "이 이메일은 이미 기존 계정에 연결되어 있습니다. 기존 로그인 방식으로 로그인한 뒤 이 계정을 연결하세요.",
        "ja": "このメールアドレスは既存アカウントに紐付いています。元の方法でログインしてから、このアカウントを連携してください。",
        "fr": "Cet e-mail est déjà associé à un compte. Connectez-vous avec la méthode d’origine, puis associez ce compte."
    },
    "identity.verify_failed.token": {
        "zh-Hans": "登录校验失败",
        "zh-Hant": "登錄校驗失敗",
        "en": "Login verification failed",
        "ko": "로그인 인증에 실패했습니다",
        "ja": "ログイン認証に失敗しました",
        "fr": "Échec de la vérification de connexion"
    },
    "identity.expired.token": {
        "zh-Hans": "登录已过期",
        "zh-Hant": "登錄已過期",
        "en": "Login expired",
        "ko": "로그인이 만료되었습니다",
        "ja": "ログインの有効期限が切れています",
        "fr": "Connexion expirée"
    },
    "identity.recognition_failed.realname": {
        "zh-Hans": "证件识别失败",
        "zh-Hant": "證件識別失敗",
        "en": "Recognition failed",
        "ko": "신분증 인식 실패",
        "ja": "本人確認に失敗しました",
        "fr": "Échec de la reconnaissance"
    },
    "identity.frequently_certified.realname": {
        "zh-Hans": "暂时无法重新认证",
        "zh-Hant": "暫時無法重新認證",
        "en": "Re-authentication is temporarily unavailable",
        "ko": "현재 재인증이 불가능합니다",
        "ja": "現在は再認証できません",
        "fr": "Nouvelle vérification temporairement indisponible"
    },
    "identity.has_certified.realname": {
        "zh-Hans": "身份已被认证",
        "zh-Hant": "身份已被認證",
        "en": "Identity has been certified",
        "ko": "이미 인증된 신원입니다",
        "ja": "本人確認済みです",
        "fr": "Identité déjà vérifiée"
    },

    "identity.with_phone.phone_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first",
        "ko": "먼저 연결을 해제해주세요",
        "ja": "先に連携を解除してください",
        "fr": "Veuillez d'abord dissocier"
    },
    "identity.already_certified.phone_bind": {
        "zh-Hans": "该号码已被绑定",
        "zh-Hant": "該號碼已被綁定",
        "en": "This number has been bound",
        "ko": "이미 등록된 번호입니다",
        "ja": "この番号は既に連携されています",
        "fr": "Ce numéro est déjà lié"
    },
    "identity.no_phone.phone_unbind": {
        "zh-Hans": "请先绑定一个手机号",
        "zh-Hant": "請先綁定一個手機號",
        "en": "Please bind a mobile phone number first",
        "ko": "먼저 휴대폰 번호를 등록해주세요",
        "ja": "先に電話番号を連携してください",
        "fr": "Veuillez d'abord lier un numéro de téléphone"
    },
    "identity.cannot_recover.phone_unbind": {
        "zh-Hans": "请先绑定一个邮箱或Apple账号，否则账号无法找回",
        "zh-Hant": "請先綁定一個郵箱或Apple帳號，否則帳號無法找回",
        "en": "Please link an email address or apple account first, otherwise the account cannot be recovered",
        "ko": "이메일 또는 Apple 계정을 먼저 연결해야 계정을 복구할 수 있습니다",
        "ja": "先にメールアドレスまたはAppleアカウントを連携してください。連携されていない場合、アカウントを復旧できません",
        "fr": "Veuillez d'abord lier une adresse e-mail ou un compte Apple, sinon le compte ne pourra pas être récupéré"
    },

    "identity.verify_failed.apple_bind": {
        "zh-Hans": "Apple 账号绑定失败，请在 系统设置-Apple账户-通过Apple登录 里删除账号后重试",
        "zh-Hant": "Apple 帳號綁定失敗，請在 系統設置-Apple帳戶-通過Apple登錄 裡刪除帳號後重識",
        "en": "Apple account binding failed, please delete the account in 'System Settings - Apple account - Sign in with Apple' and try again.",
        "ko": "Apple 계정 연결 실패. 설정에서 계정을 삭제 후 다시 시도해주세요",
        "ja": "Appleアカウントの連携に失敗しました。「設定 - Appleアカウント - Appleでサインイン」からアカウントを削除して再試行してください",
        "fr": "Échec de la liaison du compte Apple. Veuillez supprimer le compte dans « Réglages - Compte Apple - Se connecter avec Apple » puis réessayer."
    },
    "identity.with_appleID.apple_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first",
        "ko": "먼저 연결을 해제해주세요",
        "ja": "先に連携を解除してください",
        "fr": "Veuillez d'abord dissocier"
    },
    "identity.already_certified.apple_bind": {
        "zh-Hans": "该 Apple 账号已被绑定",
        "zh-Hant": "該 Apple 帳號已被綁定",
        "en": "This AppleID has been bound",
        "ko": "이미 연결된 Apple 계정입니다",
        "ja": "このAppleアカウントは既に連携されています",
        "fr": "Cet identifiant Apple est déjà lié"
    },
    "identity.no_appleID.apple_unbind": {
        "zh-Hans": "请先绑定一个Apple账号",
        "zh-Hant": "請先綁定一個Apple帳號",
        "en": "Please bind an AppleID first",
        "ko": "먼저 Apple 계정을 연결해주세요",
        "ja": "先にAppleアカウントを連携してください",
        "fr": "Veuillez d'abord lier un identifiant Apple"
    },
    "identity.cannot_recover.apple_unbind": {
        "zh-Hans": "请先绑定一个邮箱或手机号，否则账号无法找回",
        "zh-Hant": "請先綁定一個郵箱或手機號，否則帳號無法找回",
        "en": "Please link an email address or mobile phone number first, otherwise the account cannot be recovered",
        "ko": "이메일 또는 휴대폰 번호를 먼저 연결해야 계정을 복구할 수 있습니다",
        "ja": "先にメールアドレスまたは電話番号を連携してください。連携されていない場合、アカウントを復旧できません",
        "fr": "Veuillez d'abord lier une adresse e-mail ou un numéro de téléphone, sinon le compte ne pourra pas être récupéré"
    },
    "identity.verify_failed.google_bind": {
        "zh-Hans": "Google 账号绑定失败，请重试",
        "zh-Hant": "Google 帳號綁定失敗，請重試",
        "en": "Google account linking failed. Please try again.",
        "ko": "Google 계정 연결에 실패했습니다. 다시 시도해 주세요.",
        "ja": "Google アカウントの連携に失敗しました。もう一度お試しください。",
        "fr": "Échec de l’association du compte Google. Veuillez réessayer."
    },
    "identity.with_google.google_bind": {
        "zh-Hans": "请先解除已绑定的 Google 账号",
        "zh-Hant": "請先解除已綁定的 Google 帳號",
        "en": "Please unlink the current Google account first.",
        "ko": "먼저 연결된 Google 계정을 해제해 주세요.",
        "ja": "先に連携済みの Google アカウントを解除してください。",
        "fr": "Veuillez d’abord dissocier le compte Google actuel."
    },
    "identity.already_certified.google_bind": {
        "zh-Hans": "该 Google 账号已被绑定",
        "zh-Hant": "該 Google 帳號已被綁定",
        "en": "This Google account is already linked.",
        "ko": "이 Google 계정은 이미 연결되어 있습니다.",
        "ja": "この Google アカウントはすでに連携されています。",
        "fr": "Ce compte Google est déjà associé."
    },
    "identity.no_google.google_unbind": {
        "zh-Hans": "请先绑定一个 Google 账号",
        "zh-Hant": "請先綁定一個 Google 帳號",
        "en": "Please link a Google account first.",
        "ko": "먼저 Google 계정을 연결해 주세요.",
        "ja": "先に Google アカウントを連携してください。",
        "fr": "Veuillez d’abord associer un compte Google."
    },
    "identity.cannot_recover.google_unbind": {
        "zh-Hans": "请先绑定一个邮箱、手机号或 Apple 账号，否则账号无法找回",
        "zh-Hant": "請先綁定一個郵箱、手機號或 Apple 帳號，否則帳號無法找回",
        "en": "Link an email, phone number, or Apple account first so the account can be recovered.",
        "ko": "계정을 복구할 수 있도록 먼저 이메일, 전화번호 또는 Apple 계정을 연결해 주세요.",
        "ja": "アカウントを復旧できるよう、先にメールアドレス、電話番号、または Apple アカウントを連携してください。",
        "fr": "Associez d’abord un e-mail, un numéro de téléphone ou un compte Apple afin de pouvoir récupérer le compte."
    },

    "identity.with_email.email_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first",
        "ko": "먼저 연결을 해제해주세요",
        "ja": "先に連携を解除してください",
        "fr": "Veuillez d'abord dissocier"
    },
    "identity.already_certified.email_bind": {
        "zh-Hans": "该邮箱已被绑定",
        "zh-Hant": "該郵箱已被綁定",
        "en": "This email has been bound",
        "ko": "이미 등록된 이메일입니다",
        "ja": "このメールアドレスは既に連携されています",
        "fr": "Cet e-mail est déjà lié"
    },
    "identity.no_email.email_unbind": {
        "zh-Hans": "请先绑定一个邮箱",
        "zh-Hant": "請先綁定一個郵箱",
        "en": "Please bind an email first",
        "ko": "먼저 이메일을 등록해주세요",
        "ja": "先にメールアドレスを連携してください",
        "fr": "Veuillez d'abord lier un e-mail"
    },
    "identity.cannot_recover.email_unbind": {
        "zh-Hans": "请先绑定一个手机号码或Apple账号，否则账号无法找回",
        "zh-Hant": "請先綁定一個手機號碼或Apple帳號，否則帳號無法找回",
        "en": "Please link a mobile phone number or an apple account first, otherwise the account cannot be recovered",
        "ko": "휴대폰 번호 또는 Apple 계정을 먼저 연결해야 계정을 복구할 수 있습니다",
        "ja": "先に電話番号またはAppleアカウントを連携してください。連携されていない場合、アカウントを復旧できません",
        "fr": "Veuillez d'abord lier un numéro de téléphone ou un compte Apple, sinon le compte ne pourra pas être récupéré"
    },

    "identity.no_permission.internal_backend": {
        "zh-Hans": "无访问权限",
        "zh-Hant": "無訪問權限",
        "en": "No access permission",
        "ko": "접근 권한이 없습니다",
        "ja": "アクセス権限がありません",
        "fr": "Aucune autorisation d'accès"
    },
# 地区
    "region.not_found": {
        "zh-Hans": "地区不存在",
        "zh-Hant": "地區不存在",
        "en": "Region not exist",
        "ko": "지역이 존재하지 않습니다",
        "ja": "地域が存在しません",
        "fr": "La région n'existe pas"
    },
    "region.data_error": {
        "zh-Hans": "地区数据错误",
        "zh-Hant": "地區數據錯誤",
        "en": "Region data error",
        "ko": "지역 데이터 오류",
        "ja": "地域データエラー",
        "fr": "Erreur de données de région"
    },
    "region.no_events": {
        "zh-Hans": "当前地区无赛事",
        "zh-Hant": "當前地區無賽事",
        "en": "Currently no events in the region",
        "ko": "현재 지역에 진행 중인 이벤트가 없습니다",
        "ja": "現在この地域では開催中のイベントがありません",
        "fr": "Aucune compétition dans cette région pour le moment"
    },
# 赛季
    "season.not_found": {
        "zh-Hans": "赛季不存在",
        "zh-Hant": "賽季不存在",
        "en": "Season not exist",
        "ko": "시즌이 존재하지 않습니다",
        "ja": "シーズンが存在しません",
        "fr": "La saison n'existe pas"
    },
    "season.data_error": {
        "zh-Hans": "赛季数据错误",
        "zh-Hant": "賽季數據錯誤",
        "en": "Season data error",
        "ko": "시즌 데이터 오류",
        "ja": "シーズンデータエラー",
        "fr": "Erreur de données de saison"
    },
    "season.out_of_season": {
        "zh-Hans": "非赛季期",
        "zh-Hant": "非賽季期",
        "en": "Off season",
        "ko": "시즌 기간이 아닙니다",
        "ja": "シーズン期間外です",
        "fr": "Hors saison"
    },
# 赛事
    "event.not_found": {
        "zh-Hans": "赛事不存在",
        "zh-Hant": "賽事不存在",
        "en": "Event not exist",
        "ko": "이벤트가 존재하지 않습니다",
        "ja": "イベントが存在しません",
        "fr": "La compétition n'existe pas"
    },
    "event.invalid_time": {
        "zh-Hans": "赛事时间非法",
        "zh-Hant": "賽事時間非法",
        "en": "Event time is illegal",
        "ko": "이벤트 시간이 올바르지 않습니다",
        "ja": "イベント時間が不正です",
        "fr": "L'horaire de la compétition n'est pas valide"
    },
# 赛道
    "track.not_found": {
        "zh-Hans": "赛道不存在",
        "zh-Hant": "賽道不存在",
        "en": "Track not exist",
        "ko": "트랙이 존재하지 않습니다",
        "ja": "コースが存在しません",
        "fr": "Le parcours n'existe pas"
    },
    "track.invalid_time": {
        "zh-Hans": "赛道时间非法",
        "zh-Hant": "賽道時間非法",
        "en": "Invalid track time",
        "ko": "트랙 시간이 올바르지 않습니다",
        "ja": "コース時間が不正です",
        "fr": "Horaire de parcours non valide"
    },
    "track.data_error": {
        "zh-Hans": "赛道数据错误",
        "zh-Hant": "賽道數據錯誤",
        "en": "Track data error",
        "ko": "트랙 데이터 오류",
        "ja": "コースデータエラー",
        "fr": "Erreur de données de parcours"
    },
    "track.not_started": {
        "zh-Hans": "赛道尚未开放",
        "zh-Hant": "賽道尚未開放",
        "en": "Track is not open yet",
        "ko": "트랙이 아직 시작되지 않았습니다",
        "ja": "コースはまだ開始されていません",
        "fr": "Le parcours n'est pas encore ouvert"
    },
    "track.is_finished": {
        "zh-Hans": "赛道已关闭",
        "zh-Hant": "賽道已關閉",
        "en": "Track is closed",
        "ko": "트랙이 종료되었습니다",
        "ja": "コースは終了しました",
        "fr": "Le parcours est fermé"
    },
    "track.is_finished.cancel_register": {
        "zh-Hans": "赛道已关闭，无法取消",
        "zh-Hant": "賽道已關閉，無法取消",
        "en": "Track is closed, cannot cancel",
        "ko": "트랙이 종료되어 취소할 수 없습니다",
        "ja": "コースは終了しているため、キャンセルできません",
        "fr": "Le parcours est fermé, annulation impossible"
    },
# 路线
    "route.not_found": {
        "zh-Hans": "路线不存在",
        "zh-Hant": "路線不存在",
        "en": "Route not exist",
        "ko": "경로가 존재하지 않습니다",
        "ja": "ルートが存在しません",
        "fr": "L'itinéraire n'existe pas"
    },
    "route.data_error.create": {
        "zh-Hans": "路线非法，创建失败",
        "zh-Hant": "路線非法，創建失敗",
        "en": "Route invalid, creation failed",
        "ko": "경로가 잘못되었습니다, 생성에 실패했습니다",
        "ja": "ルートが不正なため、作成に失敗しました",
        "fr": "Itinéraire non valide, échec de la création"
    },
    "route.data_error.update": {
        "zh-Hans": "路线非法，修改失败",
        "zh-Hant": "路線非法，修改失敗",
        "en": "Route invalid, update failed",
        "ko": "경로가 잘못되었습니다, 수정에 실패했습니다",
        "ja": "ルートが不正なため、更新に失敗しました",
        "fr": "Itinéraire non valide, échec de la mise à jour"
    },
    "route.edit_forbidden": {
        "zh-Hans": "公开路线不可编辑",
        "zh-Hant": "公開路線不可編輯",
        "en": "Public routes cannot be edited",
        "ko": "공개된 경로는 편집할 수 없습니다",
        "ja": "公開ルートは編集できません",
        "fr": "Les itinéraires publics ne peuvent pas être modifiés"
    },
    "route.apply_forbidden": {
        "zh-Hans": "仅公开且热度达标的路线可申请",
        "zh-Hant": "僅公開且熱度達標的路線可申請",
        "en": "Only public routes with enough popularity can apply",
        "ko": "공개되고 인기가 충분한 경로만 신청할 수 있습니다",
        "ja": "公開かつ人気が一定以上のルートのみ申請できます",
        "fr": "Seuls les itinéraires publics suffisamment populaires peuvent postuler"
    },
    "route.apply_pending": {
        "zh-Hans": "该路线已有申请正在审核中",
        "zh-Hant": "該路線已有申請正在審核中",
        "en": "This route already has a pending application",
        "ko": "이 경로에는 이미 심사 중인 신청이 있습니다",
        "ja": "このルートには審査中の申請が既にあります",
        "fr": "Cet itinéraire a déjà une demande en attente"
    },
    "route.apply_not_found": {
        "zh-Hans": "申请不存在",
        "zh-Hant": "申請不存在",
        "en": "Application not found",
        "ko": "신청을 찾을 수 없습니다",
        "ja": "申請が見つかりません",
        "fr": "Demande introuvable"
    },
    "route.apply_handled": {
        "zh-Hans": "该申请已被处理",
        "zh-Hant": "該申請已被處理",
        "en": "This application has already been handled",
        "ko": "이 신청은 이미 처리되었습니다",
        "ja": "この申請は既に処理されています",
        "fr": "Cette demande a déjà été traitée"
    },
# 记录
    "record.not_found": {
        "zh-Hans": "记录不存在",
        "zh-Hant": "記錄不存在",
        "en": "Record not exist",
        "ko": "기록이 존재하지 않습니다",
        "ja": "記録が存在しません",
        "fr": "L'enregistrement n'existe pas"
    },
    "record.op_failed": {
        "zh-Hans": "操作失败",
        "zh-Hant": "操作失敗",
        "en": "Operation failed",
        "ko": "작업 실패",
        "ja": "操作に失敗しました",
        "fr": "Échec de l'opération"
    },
    "record.access_denied": {
        "zh-Hans": "该比赛结果仅对允许的用户可见",
        "zh-Hant": "該比賽結果僅對允許的用戶可見",
        "en": "This competition result is only visible to authorized users.",
        "ko": "이 경기 결과는 권한이 있는 사용자만 볼 수 있습니다.",
        "ja": "この試合結果は許可されたユーザーのみ閲覧できます。",
        "fr": "Ce résultat de compétition est réservé aux utilisateurs autorisés."
    },
    "record.data_error.leaderboard_update": {
        "zh-Hans": "排行榜写入失败",
        "zh-Hant": "排行榜寫入失敗",
        "en": "Leaderboard writing failed",
        "ko": "리더보드 저장 실패",
        "ja": "ランキングの保存に失敗しました",
        "fr": "Échec de l'écriture au classement"
    },
    "record.invalid_time": {
        "zh-Hans": "比赛时间非法",
        "zh-Hant": "比賽時間非法",
        "en": "Game time is illegal",
        "ko": "경기 시간이 올바르지 않습니다",
        "ja": "試合時間が不正です",
        "fr": "L'horaire de la course n'est pas valide"
    },
    "record.invalid.too_short": {
        "zh-Hans": "记录过短，无法保存",
        "zh-Hant": "記錄過短，無法保存",
        "en": "Record is too short to save",
        "ko": "기록이 너무 짧아 저장할 수 없습니다",
        "ja": "記録時間が短すぎるため保存できません",
        "fr": "L'enregistrement est trop court pour être sauvegardé"
    },
    "record.invalid.route_path": {
        "zh-Hans": "轨迹未按路线要求经过起点或终点检查点",
        "zh-Hant": "軌跡未按路線要求經過起點或終點檢查點",
        "en": "Track did not pass the start or end checkpoint as required",
        "ko": "경로가 출발/도착 체크포인트를 통과하지 않았습니다",
        "ja": "ルートが開始または終了チェックポイントを通過していません",
        "fr": "Le parcours n'a pas franchi le point de départ ou d'arrivée requis"
    },

    "record.status_error.cancel_register": {
        "zh-Hans": "记录状态错误，无法取消",
        "zh-Hant": "記錄狀態錯誤，無法取消",
        "en": "Record status error, cannot be cancelled",
        "ko": "기록 상태 오류로 취소할 수 없습니다",
        "ja": "記録状態エラーのため、キャンセルできません",
        "fr": "Statut de l'enregistrement incorrect, annulation impossible"
    },
    "record.status_error.start_match": {
        "zh-Hans": "记录状态错误，无法开始比赛",
        "zh-Hant": "記錄狀態錯誤，無法開始比賽",
        "en": "Record status error, cannot start competition",
        "ko": "기록 상태 오류로 경기를 시작할 수 없습니다",
        "ja": "記録状態エラーのため、試合を開始できません",
        "fr": "Statut de l'enregistrement incorrect, impossible de démarrer la compétition"
    },
    "record.status_error.finish_match": {
        "zh-Hans": "记录状态错误，无法结束比赛",
        "zh-Hant": "記錄狀態錯誤，無法結束比賽",
        "en": "Record status error, cannot finish competition",
        "ko": "기록 상태 오류로 경기를 종료할 수 없습니다",
        "ja": "記録状態エラーのため、試合を終了できません",
        "fr": "Statut de l'enregistrement incorrect, impossible de terminer la compétition"
    },

# 队伍
    "team.not_found": {
        "zh-Hans": "队伍不存在",
        "zh-Hant": "隊伍不存在",
        "en": "Team not exist",
        "ko": "팀이 존재하지 않습니다",
        "ja": "チームが存在しません",
        "fr": "L'équipe n'existe pas"
    },
    "team.data_error": {
        "zh-Hans": "队伍数据错误",
        "zh-Hant": "隊伍數據錯誤",
        "en": "Team data error",
        "ko": "팀 데이터 오류",
        "ja": "チームデータエラー",
        "fr": "Erreur de données d'équipe"
    },
    "team.op_failed.manage_team": {
        "zh-Hans": "操作失败",
        "zh-Hant": "操作失敗",
        "en": "Operation failed",
        "ko": "작업 실패",
        "ja": "操作に失敗しました",
        "fr": "Échec de l'opération"
    },

    "team.invalid_match_time": {
        "zh-Hans": "比赛时间不合法",
        "zh-Hant": "比賽時間不合法",
        "en": "The match time was illegal",
        "ko": "경기 시간이 올바르지 않습니다",
        "ja": "試合時間が不正です",
        "fr": "L'horaire de course n'est pas valide"
    },
    "team.out_of_match_time": {
        "zh-Hans": "不在队伍的有效比赛时间内",
        "zh-Hant": "不在隊伍的有效比賽時間內",
        "en": "Outside of team's valid match time",
        "ko": "팀의 유효 경기 시간 범위를 벗어났습니다",
        "ja": "チームの有効試合時間外です",
        "fr": "En dehors de la fenêtre de course valide de l'équipe"
    },
    "team.out_of_match_window": {
        "zh-Hans": "不在队伍的比赛窗口期内，无法加入",
        "zh-Hant": "不在隊伍的比賽窗口期內，無法加入",
        "en": "Cannot join, you are not in the team's match window",
        "ko": "팀의 경기 참여 시간대가 아니므로 참가할 수 없습니다",
        "ja": "チームの試合ウィンドウ外のため参加できません",
        "fr": "Impossible de rejoindre : vous n'êtes pas dans la fenêtre de course de l'équipe"
    },

    "team.member_not_enough": {
        "zh-Hans": "队伍至少需要 2 名成员哦",
        "zh-Hant": "隊伍至少需要 2 名成員哦",
        "en": "Team must have at least 2 members",
        "ko": "팀은 최소 2명 이상의 멤버가 필요합니다",
        "ja": "チームには最低2人のメンバーが必要です",
        "fr": "L'équipe doit compter au moins 2 membres"
    },
    "team.member_fulled": {
        "zh-Hans": "队伍已满",
        "zh-Hant": "隊伍已滿",
        "en": "The team is full",
        "ko": "팀 인원이 가득 찼습니다",
        "ja": "チームは満員です",
        "fr": "L'équipe est complète"
    },
    "team.already_in_members": {
        "zh-Hans": "你已在队伍中",
        "zh-Hant": "你已在隊伍中",
        "en": "You are already in the team",
        "ko": "이미 팀에 속해 있습니다",
        "ja": "既にチームに参加しています",
        "fr": "Vous êtes déjà dans l'équipe"
    },
    "team.not_in_members": {
        "zh-Hans": "你不在队伍中",
        "zh-Hant": "你不在隊伍中",
        "en": "You are not in the team",
        "ko": "팀에 속해 있지 않습니다",
        "ja": "チームに参加していません",
        "fr": "Vous n'êtes pas dans l'équipe"
    },
    "team.not_in_members.manage_team": {
        "zh-Hans": "用户不在队伍中",
        "zh-Hant": "用戶不在隊伍中",
        "en": "User is not in the team",
        "ko": "해당 사용자는 팀에 속해 있지 않습니다",
        "ja": "ユーザーはチームに参加していません",
        "fr": "L'utilisateur n'est pas dans l'équipe"
    },
    "team.already_in_applied_members": {
        "zh-Hans": "你已在申请列表中",
        "zh-Hant": "你已在申請列表中",
        "en": "You are already on the application list",
        "ko": "이미 신청 목록에 있습니다",
        "ja": "既に申請リストに入っています",
        "fr": "Vous êtes déjà sur la liste des demandes"
    },
    "team.not_in_applied_members": {
        "zh-Hans": "你不在申请列表中",
        "zh-Hant": "你不在申請列表中",
        "en": "You are not on the application list",
        "ko": "신청 목록에 없습니다",
        "ja": "申請リストに入っていません",
        "fr": "Vous n'êtes pas sur la liste des demandes"
    },
    "team.not_in_applied_members.manage_team": {
        "zh-Hans": "用户不在申请列表中",
        "zh-Hant": "用戶不在申請列表中",
        "en": "User is not on the application list",
        "ko": "해당 사용자는 신청 목록에 없습니다",
        "ja": "ユーザーは申請リストに入っていません",
        "fr": "L'utilisateur n'est pas sur la liste des demandes"
    },
    "team.is_registered.quit_team": {
        "zh-Hans": "请先取消报名",
        "zh-Hant": "請先取消報名",
        "en": "Please cancel your registration first",
        "ko": "먼저 참가 신청을 취소해주세요",
        "ja": "先に参加登録をキャンセルしてください",
        "fr": "Veuillez d'abord annuler votre inscription"
    },
    "team.repeat_register": {
        "zh-Hans": "请勿重复报名",
        "zh-Hant": "請勿重複報名",
        "en": "Please do not register repeatedly",
        "ko": "중복으로 신청할 수 없습니다",
        "ja": "重複して参加登録できません",
        "fr": "Ne vous inscrivez pas en double"
    },
    "team.repeat_cancel_register": {
        "zh-Hans": "请勿重复取消",
        "zh-Hant": "請勿重複取消",
        "en": "Please do not cancel repeatedly",
        "ko": "중복으로 취소할 수 없습니다",
        "ja": "重複してキャンセルできません",
        "fr": "N'annulez pas en double"
    },
    "team.not_all_registered.manage_team": {
        "zh-Hans": "队伍中存在未报名成员",
        "zh-Hant": "隊伍中存在未報名成員",
        "en": "There are members in the team who did not register",
        "ko": "팀 내에 아직 신청하지 않은 멤버가 있습니다",
        "ja": "チーム内に未登録のメンバーがいます",
        "fr": "Certains membres de l'équipe ne se sont pas inscrits"
    },
    "team.not_all_settled.manage_team": {
        "zh-Hans": "队伍中存在待审核成员",
        "zh-Hant": "隊伍中存在待審核成員",
        "en": "There are members in the team whose applications are pending review",
        "ko": "팀 내에 아직 검토 중인 멤버가 있습니다",
        "ja": "チーム内に審査待ちのメンバーがいます",
        "fr": "Certaines demandes d'adhésion sont en attente de validation"
    },
    "team.is_leader.quit_team": {
        "zh-Hans": "你是队长，无法退出",
        "zh-Hant": "你是隊長，無法退出",
        "en": "You cannot quit as a team leader",
        "ko": "팀장은 탈퇴할 수 없습니다",
        "ja": "リーダーは退出できません",
        "fr": "En tant que capitaine, vous ne pouvez pas quitter l'équipe"
    },

    "team.status_error": {
        "zh-Hans": "队伍状态错误",
        "zh-Hant": "隊伍狀態錯誤",
        "en": "Team status error",
        "ko": "팀 상태 오류",
        "ja": "チーム状態エラー",
        "fr": "Erreur de statut de l'équipe"
    },
    "team.status_error.enter_match": {
        "zh-Hans": "队伍未处于比赛状态，无法开始",
        "zh-Hant": "隊伍未處於比賽狀態，無法開始",
        "en": "Game is not in ready-for-match status, cannot start",
        "ko": "팀이 경기 시작 상태가 아니므로 시작할 수 없습니다",
        "ja": "チームが試合開始状態ではないため開始できません",
        "fr": "La partie n'est pas en statut « prêt pour la course », impossible de démarrer"
    },
    "team.status_not_prepared.join_team": {
        "zh-Hans": "队伍未处于准备状态，不可加入",
        "zh-Hant": "隊伍未處於準備狀態，不可加入",
        "en": "Team is not in prepared status, cannot join",
        "ko": "팀이 준비 상태가 아니므로 참가할 수 없습니다",
        "ja": "チームが準備状態ではないため参加できません",
        "fr": "L'équipe n'est pas en statut « prête », impossible de la rejoindre"
    },
    "team.status_not_prepared.manage_team": {
        "zh-Hans": "队伍已锁定，不可修改",
        "zh-Hant": "隊伍已鎖定，不可修改",
        "en": "Team is locked and cannot be changed",
        "ko": "팀이 잠겨 있어 수정할 수 없습니다",
        "ja": "チームはロックされているため変更できません",
        "fr": "L'équipe est verrouillée et ne peut pas être modifiée"
    },
    "team.status_not_locked": {
        "zh-Hans": "队伍未处于锁定状态",
        "zh-Hant": "隊伍未處於鎖定狀態",
        "en": "Team is not locked",
        "ko": "팀이 잠금 상태가 아닙니다",
        "ja": "チームはロック状態ではありません",
        "fr": "L'équipe n'est pas verrouillée"
    },
    "team.status_not_ready": {
        "zh-Hans": "队伍未处于就绪状态",
        "zh-Hant": "隊伍未處於就緒狀態",
        "en": "Team is not ready",
        "ko": "팀이 준비 상태가 아닙니다",
        "ja": "チームは準備完了状態ではありません",
        "fr": "L'équipe n'est pas prête"
    },
    "team.status_on_recording": {
        "zh-Hans": "比赛进行中",
        "zh-Hant": "比賽進行中",
        "en": "Game is in progress",
        "ko": "경기가 진행 중입니다",
        "ja": "試合進行中です",
        "fr": "La partie est en cours"
    },
    "team.status_expired": {
        "zh-Hans": "队伍已过期",
        "zh-Hant": "隊伍已過期",
        "en": "Team has expired",
        "ko": "팀이 만료되었습니다",
        "ja": "チームの有効期限が切れています",
        "fr": "L'équipe a expiré"
    },
    "team.match_recording.quit_team": {
        "zh-Hans": "比赛进行中，无法退出",
        "zh-Hant": "比賽進行中，無法退出",
        "en": "Game is in progress, cannot quit",
        "ko": "경기 진행 중에는 탈퇴할 수 없습니다",
        "ja": "試合中のため退出できません",
        "fr": "La partie est en cours, impossible de quitter"
    },
    "team.match_recording.cancel_register": {
        "zh-Hans": "比赛进行中，无法取消",
        "zh-Hant": "比賽進行中，無法取消",
        "en": "Game is in progress, cannot cancel",
        "ko": "경기 진행 중에는 취소할 수 없습니다",
        "ja": "試合中のためキャンセルできません",
        "fr": "La partie est en cours, annulation impossible"
    },
    "team.match_recording.manage_team": {
        "zh-Hans": "队伍处于比赛状态，无法修改",
        "zh-Hant": "隊伍處於比賽狀態，無法修改",
        "en": "Game is in ready-for-match status, cannot be changed",
        "ko": "팀이 경기 상태이므로 수정할 수 없습니다",
        "ja": "チームは試合状態のため変更できません",
        "fr": "La partie est en statut « prêt pour la course », modification impossible"
    },
    

# 资产
    "asset.data_error": {
        "zh-Hans": "资产数据错误",
        "zh-Hant": "資產數據錯誤",
        "en": "Asset data error",
        "ko": "자산 데이터 오류",
        "ja": "資産データエラー",
        "fr": "Erreur de données de ressource"
    },
    "asset.not_found": {
        "zh-Hans": "资产不存在",
        "zh-Hant": "資產不存在",
        "en": "Asset not exist",
        "ko": "자산이 존재하지 않습니다",
        "ja": "資産が存在しません",
        "fr": "La ressource n'existe pas"
    },
    "asset.not_enough": {
        "zh-Hans": "{asset_type}不足",
        "zh-Hant": "{asset_type}不足",
        "en": "Not enough {asset_type}s",
        "ko": "{asset_type}이(가) 부족합니다",
        "ja": "{asset_type}が足りません",
        "fr": "Pas assez de {asset_type}"
    },
    "asset.off_shelves": {
        "zh-Hans": "资产已下架",
        "zh-Hant": "資產已下架",
        "en": "Asset has been delisted",
        "ko": "자산이 판매 중단되었습니다",
        "ja": "資産は販売停止となりました",
        "fr": "La ressource a été retirée"
    },
    "asset.upgrade_failed": {
        "zh-Hans": "升级失败",
        "zh-Hant": "升級失敗",
        "en": "Upgrade failed",
        "ko": "업그레이드 실패",
        "ja": "アップグレードに失敗しました",
        "fr": "Échec de l'amélioration"
    },

    "ccasset.coin": {
        "zh-Hans": "金币",
        "zh-Hant": "金幣",
        "en": "gold coin",
        "ko": "코인",
        "ja": "ゴールドコイン",
        "fr": "pièce d'or"
    },
    "ccasset.coupon": {
        "zh-Hans": "点券",
        "zh-Hant": "點券",
        "en": "point",
        "ko": "포인트",
        "ja": "ポイント券",
        "fr": "point"
    },
    "ccasset.voucher": {
        "zh-Hans": "金券",
        "zh-Hant": "金券",
        "en": "gold point",
        "ko": "바우처",
        "ja": "ゴールドチケット",
        "fr": "point d'or"
    },
    "ccasset.stone1": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material",
        "ko": "업그레이드 재료",
        "ja": "アップグレード素材",
        "fr": "matériau d'amélioration"
    },
    "ccasset.stone2": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material",
        "ko": "업그레이드 재료",
        "ja": "アップグレード素材",
        "fr": "matériau d'amélioration"
    },
    "ccasset.stone3": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material",
        "ko": "업그레이드 재료",
        "ja": "アップグレード素材",
        "fr": "matériau d'amélioration"
    },
    "cpasset.team_card": {
        "zh-Hans": "组队卡",
        "zh-Hant": "組隊卡",
        "en": "team card",
        "ko": "팀 카드",
        "ja": "チームカード",
        "fr": "carte d'équipe"
    },
    "cpasset.registration_card": {
        "zh-Hans": "报名卡",
        "zh-Hant": "報名卡",
        "en": "registration card",
        "ko": "참가 카드",
        "ja": "登録カード",
        "fr": "carte d'inscription"
    },
    "cpasset.route_card": {
        "zh-Hans": "路线创建卡",
        "zh-Hant": "路線建立卡",
        "en": "Route creation card",
        "ko": "경로 생성권",
        "ja": "ルート作成カード",
        "fr": "carte de création d'itinéraire"
    },
# 排行榜
    "leaderboard.expired": {
        "zh-Hans": "排行榜数据已过期,请刷新",
        "zh-Hant": "排行榜數據已過期，請刷新",
        "en": "The leaderboard data has expired, please refresh",
        "ko": "리더보드 데이터가 만료되었습니다. 새로고침해주세요",
        "ja": "ランキングデータの有効期限が切れました。再読み込みしてください",
        "fr": "Les données du classement ont expiré, veuillez actualiser"
    },
# 邮件
    "mail.not_found": {
        "zh-Hans": "邮件不存在",
        "zh-Hant": "郵件不存在",
        "en": "Email not exist",
        "ko": "메일이 존재하지 않습니다",
        "ja": "メールが存在しません",
        "fr": "L'e-mail n'existe pas"
    },
# IAP
    "iap_subscription.verify_failed.purchase": {
        "zh-Hans": "订阅校验失败，请及时反馈",
        "zh-Hant": "訂閱校驗失敗，請及時反饋",
        "en": "Subscription verification failed, please provide feedback promptly",
        "ko": "구독 검증 실패, 문의해주세요",
        "ja": "サブスクリプション認証に失敗しました。早めにご連絡ください",
        "fr": "Échec de la vérification de l'abonnement, merci de nous le signaler rapidement"
    },
    "iap_coupon.verify_failed.purchase": {
        "zh-Hans": "购买校验失败，请及时反馈",
        "zh-Hant": "購買校驗失敗，請及時反饋",
        "en": "Purchase verification failed, please provide feedback promptly",
        "ko": "구매 검증 실패, 문의해주세요",
        "ja": "購入認証に失敗しました。早めにご連絡ください",
        "fr": "Échec de la vérification de l'achat, merci de nous le signaler rapidement"
    },
# 反馈
    "feedback.submission_failed": {
        "zh-Hans": "提交失败，请重试",
        "zh-Hant": "提交失敗，請重識",
        "en": "Submission failed, please try again.",
        "ko": "제출 실패, 다시 시도해주세요",
        "ja": "送信に失敗しました。再試行してください",
        "fr": "Échec de l'envoi, veuillez réessayer."
    },
# 奖励领取
    "reward.expired.mail": {
        "zh-Hans": "奖励过期啦，下次记得早点领哦",
        "zh-Hant": "獎勵過期啦，下次記得早點領喔",
        "en": "The reward has expired, remember to claim it earlier next time",
        "ko": "보상이 만료되었습니다. 다음에는 더 빨리 수령해주세요",
        "ja": "報酬の有効期限が切れました。次回は早めに受け取りましょう",
        "fr": "La récompense a expiré ; pensez à la récupérer plus tôt la prochaine fois"
    },
    "reward.data_error": {
        "zh-Hans": "领取失败",
        "zh-Hant": "領取失敗",
        "en": "Failed to claim",
        "ko": "보상 수령 실패",
        "ja": "受け取りに失敗しました",
        "fr": "Échec de la récupération"
    },
    "reward.no_auth.sign_in": {
        "zh-Hans": "您还不是订阅会员哦",
        "zh-Hant": "您還不是訂閱會員喔",
        "en": "You are not a subscriber yet",
        "ko": "아직 구독 회원이 아닙니다",
        "ja": "まだサブスク会員ではありません",
        "fr": "Vous n'êtes pas encore abonné"
    },
    "reward.repeat_claimed": {
        "zh-Hans": "请勿重复领取",
        "zh-Hant": "請勿重複領取",
        "en": "Please do not claim it repeatedly",
        "ko": "이미 수령한 보상입니다",
        "ja": "重複して受け取ることはできません",
        "fr": "Ne la récupérez pas en double"
    },
# 三方服务
    "sms.too_frequent": {
        "zh-Hans": "验证码发送过于频繁，请稍后再试",
        "zh-Hant": "驗證碼發送失敗，請稍後再試",
        "en": "Verification code failed to send, please try again later.",
        "ko": "인증 코드 요청이 너무 많습니다. 잠시 후 다시 시도해주세요",
        "ja": "認証コードの送信が多すぎます。しばらくしてから再試行してください",
        "fr": "Échec de l'envoi du code, veuillez réessayer plus tard."
    },
    "sms.service_error": {
        "zh-Hans": "验证码发送失败",
        "zh-Hant": "驗證碼發送失敗",
        "en": "Verification code failed to send",
        "ko": "인증 코드 전송에 실패했습니다",
        "ja": "認証コードの送信に失敗しました",
        "fr": "Échec de l'envoi du code de vérification"
    },
    "apple.server_timeout": {
        "zh-Hans": "服务器连接超时",
        "zh-Hant": "伺服器連線逾時",
        "en": "Server connection timed out",
        "ko": "서버 연결 시간이 초과되었습니다",
        "ja": "サーバー接続がタイムアウトしました",
        "fr": "Délai de connexion au serveur dépassé"
    },
    "apple.server_error": {
        "zh-Hans": "服务器连接错误",
        "zh-Hant": "伺服器連線錯誤",
        "en": "Server connection error",
        "ko": "서버 연결 오류",
        "ja": "サーバー接続エラー",
        "fr": "Erreur de connexion au serveur"
    },
    "oss.error.upload": {
        "zh-Hans": "上传失败",
        "zh-Hant": "上傳失敗",
        "en": "Upload failed",
        "ko": "업로드 실패",
        "ja": "アップロードに失敗しました",
        "fr": "Échec du téléversement"
    },
# 系统
    "sys.unknown_error": {
        "zh-Hans": "未知错误",
        "zh-Hant": "未知錯誤",
        "en": "Unknown error",
        "ko": "알 수 없는 오류가 발생했습니다",
        "ja": "不明なエラーが発生しました",
        "fr": "Erreur inconnue"
    },
    "sys.request_timeout": {
        "zh-Hans": "请求超时，请重试",
        "zh-Hant": "請求超時，請重試",
        "en": "Request timed out, please try again.",
        "ko": "요청 시간이 초과되었습니다. 다시 시도해주세요",
        "ja": "リクエストがタイムアウトしました。再試行してください",
        "fr": "Délai de la requête dépassé, veuillez réessayer."
    }
}
