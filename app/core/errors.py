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

    # 第三方服务
    SMS_SERVICE_ERROR = 5001
    EMAIL_SERVICE_ERROR = 5002

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
        "en": "Image is oversize, please try again."
    },
# 用户
    "user.not_found": {
        "zh-Hans": "用户不存在",
        "zh-Hant": "用戶不存在",
        "en": "User does not exist"
    },
    "user.info_error": {
        "zh-Hans": "用户信息错误",
        "zh-Hant": "用戶信息錯誤",
        "en": "User info error"
    },
    "user.follow_self": {
        "zh-Hans": "不能关注自己",
        "zh-Hant": "不能關注自己",
        "en": "Cannot follow yourself"
    },
    "user.cancel_follow_self": {
        "zh-Hans": "不能取消关注自己",
        "zh-Hant": "不能取消關注自己",
        "en": "Cannot cancel follow yourself"
    },
    "user.repeat_follow": {
        "zh-Hans": "请勿重复关注",
        "zh-Hant": "請勿重複關注",
        "en": "Do not follow repeatedly"
    },
    "user.banned": {
        "zh-Hans": "账号已封禁\n剩余时间：{remaining}",
        "zh-Hant": "帳號已封禁\n剩餘時間：{remaining}",
        "en": "Account has been banned\nremaining time:{remaining}"
    },
# 身份校验
    "identity.verify_failed.test_account": {
        "zh-Hans": "账号信息错误",
        "zh-Hant": "帳號信息錯誤",
        "en": "Account info error"
    },
    "identity.verify_failed.sms": {
        "zh-Hans": "验证码错误",
        "zh-Hant": "驗證碼錯誤",
        "en": "Verification code error"
    },
    "identity.verify_failed.apple": {
        "zh-Hans": "Apple 登录校验失败",
        "zh-Hant": "Apple 登錄校驗失敗",
        "en": "Apple login verification failed"
    },
    "identity.verify_failed.token": {
        "zh-Hans": "登录校验失败",
        "zh-Hant": "登錄校驗失敗",
        "en": "Login verification failed"
    },
    "identity.expired.token": {
        "zh-Hans": "登录已过期",
        "zh-Hant": "登錄已過期",
        "en": "Login expired"
    },
    "identity.recognition_failed.realname": {
        "zh-Hans": "证件识别失败",
        "zh-Hant": "證件識別失敗",
        "en": "Recognition failed"
    },
    "identity.frequently_certified.realname": {
        "zh-Hans": "暂时无法重新认证",
        "zh-Hant": "暫時無法重新認證",
        "en": "Re-authentication is temporarily unavailable"
    },
    "identity.has_certified.realname": {
        "zh-Hans": "身份已被认证",
        "zh-Hant": "身份已被認證",
        "en": "Identity has been certified"
    },

    "identity.with_phone.phone_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first"
    },
    "identity.already_certified.phone_bind": {
        "zh-Hans": "该号码已被绑定",
        "zh-Hant": "該號碼已被綁定",
        "en": "This number has been bound"
    },
    "identity.no_phone.phone_unbind": {
        "zh-Hans": "请先绑定一个手机号",
        "zh-Hant": "請先綁定一個手機號",
        "en": "Please bind a mobile phone number first"
    },
    "identity.cannot_recover.phone_unbind": {
        "zh-Hans": "请先绑定一个邮箱或Apple账号，否则账号无法找回",
        "zh-Hant": "請先綁定一個郵箱或Apple帳號，否則帳號無法找回",
        "en": "Please link an email address or apple account first, otherwise the account cannot be recovered"
    },

    "identity.verify_failed.apple_bind": {
        "zh-Hans": "Apple 账号绑定失败，请在 系统设置-Apple账户-通过Apple登录 里删除账号后重试",
        "zh-Hant": "Apple 帳號綁定失敗，請在 系統設置-Apple帳戶-通過Apple登錄 裡刪除帳號後重識",
        "en": "Apple account binding failed, please delete the account in 'System Settings - Apple account - Sign in with Apple' and try again."
    },
    "identity.with_appleID.apple_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first"
    },
    "identity.already_certified.apple_bind": {
        "zh-Hans": "该 Apple 账号已被绑定",
        "zh-Hant": "該 Apple 帳號已被綁定",
        "en": "This AppleID has been bound"
    },
    "identity.no_appleID.apple_unbind": {
        "zh-Hans": "请先绑定一个Apple账号",
        "zh-Hant": "請先綁定一個Apple帳號",
        "en": "Please bind an AppleID first"
    },
    "identity.cannot_recover.apple_unbind": {
        "zh-Hans": "请先绑定一个邮箱或手机号，否则账号无法找回",
        "zh-Hant": "請先綁定一個郵箱或手機號，否則帳號無法找回",
        "en": "Please link an email address or mobile phone number first, otherwise the account cannot be recovered"
    },

    "identity.with_email.email_bind": {
        "zh-Hans": "请先解除绑定",
        "zh-Hant": "請先解除綁定",
        "en": "Please unbind first"
    },
    "identity.already_certified.email_bind": {
        "zh-Hans": "该邮箱已被绑定",
        "zh-Hant": "該郵箱已被綁定",
        "en": "This email has been bound"
    },
    "identity.no_email.email_unbind": {
        "zh-Hans": "请先绑定一个邮箱",
        "zh-Hant": "請先綁定一個郵箱",
        "en": "Please bind an email first"
    },
    "identity.cannot_recover.email_unbind": {
        "zh-Hans": "请先绑定一个手机号码或Apple账号，否则账号无法找回",
        "zh-Hant": "請先綁定一個手機號碼或Apple帳號，否則帳號無法找回",
        "en": "Please link a mobile phone number or an apple account first, otherwise the account cannot be recovered"
    },

    "identity.no_permission.internal_backend": {
        "zh-Hans": "无访问权限",
        "zh-Hant": "無訪問權限",
        "en": "No access permission"
    },
# 地区
    "region.not_found": {
        "zh-Hans": "地区不存在",
        "zh-Hant": "地區不存在",
        "en": "Region does not exist"
    },
    "region.data_error": {
        "zh-Hans": "地区数据错误",
        "zh-Hant": "地區數據錯誤",
        "en": "Region data error"
    },
    "region.no_events": {
        "zh-Hans": "当前地区无赛事",
        "zh-Hant": "當前地區無賽事",
        "en": "Currently no events in the region"
    },
# 赛季
    "season.not_found": {
        "zh-Hans": "赛季不存在",
        "zh-Hant": "賽季不存在",
        "en": "Season does not exist"
    },
    "season.data_error": {
        "zh-Hans": "赛季数据错误",
        "zh-Hant": "賽季數據錯誤",
        "en": "Season data error"
    },
    "season.out_of_season": {
        "zh-Hans": "非赛季期",
        "zh-Hant": "非賽季期",
        "en": "Off season"
    },
# 赛事
    "event.not_found": {
        "zh-Hans": "赛事不存在",
        "zh-Hant": "賽事不存在",
        "en": "Event does not exist"
    },
    "event.invalid_time": {
        "zh-Hans": "赛事时间非法",
        "zh-Hant": "賽事時間非法",
        "en": "Event time is illegal"
    },
# 赛道
    "track.not_found": {
        "zh-Hans": "赛道不存在",
        "zh-Hant": "賽道不存在",
        "en": "Track does not exist"
    },
    "track.invalid_time": {
        "zh-Hans": "赛道时间非法",
        "zh-Hant": "賽道時間非法",
        "en": "Invalid track time"
    },
    "track.data_error": {
        "zh-Hans": "赛道数据错误",
        "zh-Hant": "賽道數據錯誤",
        "en": "Track data error"
    },
    "track.not_started": {
        "zh-Hans": "赛道尚未开放",
        "zh-Hant": "賽道尚未開放",
        "en": "Track is not open yet"
    },
    "track.is_finished": {
        "zh-Hans": "赛道已关闭",
        "zh-Hant": "賽道已關閉",
        "en": "Track is closed"
    },
    "track.is_finished.cancel_register": {
        "zh-Hans": "赛道已关闭，无法取消",
        "zh-Hant": "賽道已關閉，無法取消",
        "en": "Track is closed, cannot cancel"
    },
# 记录
    "record.not_found": {
        "zh-Hans": "记录不存在",
        "zh-Hant": "記錄不存在",
        "en": "Record does not exist"
    },
    "record.op_failed": {
        "zh-Hans": "操作失败",
        "zh-Hant": "操作失敗",
        "en": "Operation failed"
    },
    "record.data_error.leaderboard_update": {
        "zh-Hans": "排行榜写入失败",
        "zh-Hant": "排行榜寫入失敗",
        "en": "Leaderboard writing failed"
    },
    "record.invalid_time": {
        "zh-Hans": "比赛时间非法",
        "zh-Hant": "比賽時間非法",
        "en": "Game time is illegal"
    },

    "record.status_error.cancel_register": {
        "zh-Hans": "记录状态错误，无法取消",
        "zh-Hant": "記錄狀態錯誤，無法取消",
        "en": "Record status error, cannot be cancelled"
    },
    "record.status_error.start_match": {
        "zh-Hans": "记录状态错误，无法开始比赛",
        "zh-Hant": "記錄狀態錯誤，無法開始比賽",
        "en": "Record status error, cannot start competition"
    },
    "record.status_error.finish_match": {
        "zh-Hans": "记录状态错误，无法结束比赛",
        "zh-Hant": "記錄狀態錯誤，無法結束比賽",
        "en": "Record status error, cannot finish competition"
    },

# 队伍
    "team.not_found": {
        "zh-Hans": "队伍不存在",
        "zh-Hant": "隊伍不存在",
        "en": "Team does not exist"
    },
    "team.data_error": {
        "zh-Hans": "队伍数据错误",
        "zh-Hant": "隊伍數據錯誤",
        "en": "Team data error"
    },
    "team.op_failed.manage_team": {
        "zh-Hans": "操作失败",
        "zh-Hant": "操作失敗",
        "en": "Operation failed"
    },

    "team.invalid_match_time": {
        "zh-Hans": "比赛时间不合法",
        "zh-Hant": "比賽時間不合法",
        "en": "The match time was illegal"
    },
    "team.out_of_match_time": {
        "zh-Hans": "不在队伍的有效比赛时间内",
        "zh-Hant": "不在隊伍的有效比賽時間內",
        "en": "Outside of team's valid match time"
    },
    "team.out_of_match_window": {
        "zh-Hans": "不在队伍的比赛窗口期内，无法加入",
        "zh-Hant": "不在隊伍的比賽窗口期內，無法加入",
        "en": "Cannot join, you are not in the team's match window"
    },

    "team.member_not_enough": {
        "zh-Hans": "队伍至少需要 2 名成员哦",
        "zh-Hant": "隊伍至少需要 2 名成員哦",
        "en": "Team must have at least 2 members"
    },
    "team.member_fulled": {
        "zh-Hans": "队伍已满",
        "zh-Hant": "隊伍已滿",
        "en": "The team is full"
    },
    "team.already_in_members": {
        "zh-Hans": "你已在队伍中",
        "zh-Hant": "你已在隊伍中",
        "en": "You are already in the team"
    },
    "team.not_in_members": {
        "zh-Hans": "你不在队伍中",
        "zh-Hant": "你不在隊伍中",
        "en": "You are not in the team"
    },
    "team.not_in_members.manage_team": {
        "zh-Hans": "用户不在队伍中",
        "zh-Hant": "用戶不在隊伍中",
        "en": "User is not in the team"
    },
    "team.already_in_applied_members": {
        "zh-Hans": "你已在申请列表中",
        "zh-Hant": "你已在申請列表中",
        "en": "You are already on the application list"
    },
    "team.not_in_applied_members": {
        "zh-Hans": "你不在申请列表中",
        "zh-Hant": "你不在申請列表中",
        "en": "You are not on the application list"
    },
    "team.not_in_applied_members.manage_team": {
        "zh-Hans": "用户不在申请列表中",
        "zh-Hant": "用戶不在申請列表中",
        "en": "User is not on the application list"
    },
    "team.is_registered.quit_team": {
        "zh-Hans": "请先取消报名",
        "zh-Hant": "請先取消報名",
        "en": "Please cancel your registration first"
    },
    "team.repeat_register": {
        "zh-Hans": "请勿重复报名",
        "zh-Hant": "請勿重複報名",
        "en": "Please do not register repeatedly"
    },
    "team.repeat_cancel_register": {
        "zh-Hans": "请勿重复取消",
        "zh-Hant": "請勿重複取消",
        "en": "Please do not cancel repeatedly"
    },
    "team.not_all_registered.manage_team": {
        "zh-Hans": "队伍中存在未报名成员",
        "zh-Hant": "隊伍中存在未報名成員",
        "en": "There are members in the team who did not register"
    },
    "team.not_all_settled.manage_team": {
        "zh-Hans": "队伍中存在待审核成员",
        "zh-Hant": "隊伍中存在待審核成員",
        "en": "There are members in the team whose applications are pending review"
    },
    "team.is_leader.quit_team": {
        "zh-Hans": "你是队长，无法退出",
        "zh-Hant": "你是隊長，無法退出",
        "en": "You cannot quit as a team leader"
    },

    "team.status_error": {
        "zh-Hans": "队伍状态错误",
        "zh-Hant": "隊伍狀態錯誤",
        "en": "Team status error"
    },
    "team.status_error.enter_match": {
        "zh-Hans": "队伍未处于比赛状态，无法开始",
        "zh-Hant": "隊伍未處於比賽狀態，無法開始",
        "en": "Game is not in ready-for-match status, cannot start"
    },
    "team.status_not_prepared.join_team": {
        "zh-Hans": "队伍未处于准备状态，不可加入",
        "zh-Hant": "隊伍未處於準備狀態，不可加入",
        "en": "Team is not in prepared status, cannot join"
    },
    "team.status_not_prepared.manage_team": {
        "zh-Hans": "队伍已锁定，不可修改",
        "zh-Hant": "隊伍已鎖定，不可修改",
        "en": "Team is locked and cannot be changed"
    },
    "team.status_not_locked": {
        "zh-Hans": "队伍未处于锁定状态",
        "zh-Hant": "隊伍未處於鎖定狀態",
        "en": "Team is not locked"
    },
    "team.status_not_ready": {
        "zh-Hans": "队伍未处于就绪状态",
        "zh-Hant": "隊伍未處於就緒狀態",
        "en": "Team is not ready"
    },
    "team.status_on_recording": {
        "zh-Hans": "比赛进行中",
        "zh-Hant": "比賽進行中",
        "en": "Game is in progress"
    },
    "team.status_expired": {
        "zh-Hans": "队伍已过期",
        "zh-Hant": "隊伍已過期",
        "en": "Team has expired"
    },
    "team.match_recording.quit_team": {
        "zh-Hans": "比赛进行中，无法退出",
        "zh-Hant": "比賽進行中，無法退出",
        "en": "Game is in progress, cannot quit"
    },
    "team.match_recording.cancel_register": {
        "zh-Hans": "比赛进行中，无法取消",
        "zh-Hant": "比賽進行中，無法取消",
        "en": "Game is in progress, cannot cancel"
    },
    "team.match_recording.manage_team": {
        "zh-Hans": "队伍处于比赛状态，无法修改",
        "zh-Hant": "隊伍處於比賽狀態，無法修改",
        "en": "Game is in ready-for-match status, cannot be changed"
    },
    

# 资产
    "asset.data_error": {
        "zh-Hans": "资产数据错误",
        "zh-Hant": "資產數據錯誤",
        "en": "Asset data error"
    },
    "asset.not_found": {
        "zh-Hans": "资产不存在",
        "zh-Hant": "資產不存在",
        "en": "Asset does not exist"
    },
    "asset.not_enough": {
        "zh-Hans": "{asset_type}不足",
        "zh-Hant": "{asset_type}不足",
        "en": "Not enough {asset_type}s"
    },
    "asset.off_shelves": {
        "zh-Hans": "资产已下架",
        "zh-Hant": "資產已下架",
        "en": "Asset has been delisted"
    },
    "asset.upgrade_failed": {
        "zh-Hans": "asset.upgrade_failed",
        "zh-Hant": "升級失敗",
        "en": "Upgrade failed"
    },

    "ccasset.coin": {
        "zh-Hans": "金币",
        "zh-Hant": "金幣",
        "en": "gold coin"
    },
    "ccasset.coupon": {
        "zh-Hans": "点券",
        "zh-Hant": "點券",
        "en": "point"
    },
    "ccasset.voucher": {
        "zh-Hans": "金券",
        "zh-Hant": "金券",
        "en": "gold point"
    },
    "ccasset.stone1": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material"
    },
    "ccasset.stone2": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material"
    },
    "ccasset.stone3": {
        "zh-Hans": "升级材料",
        "zh-Hant": "升級材料",
        "en": "Upgrade material"
    },
    "cpasset.team_card": {
        "zh-Hans": "组队卡",
        "zh-Hant": "組隊卡",
        "en": "team card"
    },
    "cpasset.registration_card": {
        "zh-Hans": "报名卡",
        "zh-Hant": "報名卡",
        "en": "registration card"
    },
# 排行榜
    "leaderboard.expired": {
        "zh-Hans": "排行榜数据已过期,请刷新",
        "zh-Hant": "排行榜數據已過期，請刷新",
        "en": "The leaderboard data has expired, please refresh"
    },
# 邮件
    "mail.not_found": {
        "zh-Hans": "邮件不存在",
        "zh-Hant": "郵件不存在",
        "en": "Email does not exist"
    },
# IAP
    "iap_subscription.verify_failed.purchase": {
        "zh-Hans": "订阅校验失败，请及时反馈",
        "zh-Hant": "訂閱校驗失敗，請及時反饋",
        "en": "Subscription verification failed, please provide feedback promptly"
    },
    "iap_coupon.verify_failed.purchase": {
        "zh-Hans": "购买校验失败，请及时反馈",
        "zh-Hant": "購買校驗失敗，請及時反饋",
        "en": "Purchase verification failed, please provide feedback promptly"
    },
# 反馈
    "feedback.submission_failed": {
        "zh-Hans": "提交失败，请重试",
        "zh-Hant": "提交失敗，請重識",
        "en": "Submission failed, please try again."
    },
# 奖励领取
    "reward.expired.mail": {
        "zh-Hans": "奖励过期啦，下次记得早点领哦",
        "zh-Hant": "獎勵過期啦，下次記得早點領喔",
        "en": "The reward has expired, remember to claim it earlier next time"
    },
    "reward.data_error": {
        "zh-Hans": "领取失败",
        "zh-Hant": "領取失敗",
        "en": "Failed to claim"
    },
    "reward.no_auth.sign_in": {
        "zh-Hans": "您还不是订阅会员哦",
        "zh-Hant": "您還不是訂閱會員喔",
        "en": "You are not a subscriber yet"
    },
    "reward.repeat_claimed": {
        "zh-Hans": "请勿重复领取",
        "zh-Hant": "請勿重複領取",
        "en": "Please do not claim it repeatedly"
    },
# 三方服务
    "sms.service_error": {
        "zh-Hans": "验证码发送失败",
        "zh-Hant": "驗證碼發送失敗",
        "en": "Verification code failed to send"
    },
# 系统
    "sys.unknown_error": {
        "zh-Hans": "未知错误",
        "zh-Hant": "未知錯誤",
        "en": "Unknown error"
    },
    "sys.request_timeout": {
        "zh-Hans": "请求超时，请重试",
        "zh-Hant": "請求超時，請重試",
        "en": "Request timed out, please try again."
    }
}