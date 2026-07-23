from app.db.models.asset import CouponRechargeTransaction
from app.db.models.user import User, UserSubscription, SubscriptionEvent
from app.core.errors import ErrorCode
from app.core.config import settings
from app.schemas.base import BizException
from app.schemas.user import SubscriptionStatusResponse, SubscriptionQueryInfo, SubscriptionEventType
from app.schemas.asset import AssetOperation, CouponShopResponse, CouponShopInfo
from app.schemas.common import CCAssetType
from app.crud.user import get_user_by_id, get_user_by_iap_token, get_subscription_event_by_notification_uuid
from app.crud.asset_manage import get_coupon_prices_all, reward_ccasset, get_coupon_price
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.services.app_store_api_tool import (
    query_user_subscroption_status,
    verify_and_decode_transaction_service,
    verify_and_decode_notification_service,
)
import uuid, random, math, json, os, logging

logger = logging.getLogger(__name__)


def _subscription_event_type(raw_notification_type: str | None, auto_renew: bool) -> SubscriptionEventType:
    if raw_notification_type == "SUBSCRIBED":
        return SubscriptionEventType.created
    if raw_notification_type == "DID_RENEW":
        return SubscriptionEventType.renewed
    if raw_notification_type in {"REFUND", "REVOKE"}:
        return SubscriptionEventType.refunded
    if raw_notification_type == "DID_CHANGE_RENEWAL_STATUS":
        return SubscriptionEventType.auto_renew_on if auto_renew else SubscriptionEventType.auto_renew_off
    if raw_notification_type == "GRACE_PERIOD_EXPIRED":
        return SubscriptionEventType.grace_ended
    if raw_notification_type == "DID_FAIL_TO_RENEW":
        return SubscriptionEventType.grace_started
    return SubscriptionEventType.renewed


async def handle_app_store_notification_service(db: AsyncSession, signed_payload: str) -> bool:
    """处理并持久化已验证的 App Store Server Notifications V2 通知。"""
    notification, verifier = verify_and_decode_notification_service(signed_payload)
    if notification is None or verifier is None:
        logger.warning("Discarded an App Store notification with an invalid signature")
        return False

    data = notification.data
    if not data or not data.signedTransactionInfo or not data.signedRenewalInfo:
        # TEST 以及非订阅事件不改变订阅权益。
        return True

    try:
        transaction = verifier.verify_and_decode_signed_transaction(data.signedTransactionInfo)
        renewal = verifier.verify_and_decode_renewal_info(data.signedRenewalInfo)
    except Exception:
        logger.exception("Unable to verify nested App Store subscription notification data")
        return False

    # 消耗型商品等非订阅交易没有续期时间，不应进入订阅账本。
    if not transaction.expiresDate or not transaction.appAccountToken:
        return True

    notification_uuid = notification.notificationUUID
    async with db.begin():
        if notification_uuid and await get_subscription_event_by_notification_uuid(db, notification_uuid):
            return True

        user = await get_user_by_iap_token(db, str(transaction.appAccountToken))
        if user is None:
            logger.warning("App Store notification has no matching app account token")
            return True

        started_at = (
            datetime.fromtimestamp(renewal.recentSubscriptionStartDate / 1000, tz=timezone.utc)
            if renewal.recentSubscriptionStartDate
            else None
        )
        expired_at = datetime.fromtimestamp(transaction.expiresDate / 1000, tz=timezone.utc)
        auto_renew = renewal.autoRenewStatus == 1
        is_active = (
            data.rawStatus in (1, 4)
            and transaction.revocationDate is None
            and expired_at > datetime.now(timezone.utc)
        )

        subscription = user.subscription_info
        if subscription is None:
            subscription = UserSubscription(user_id=user.id)
            db.add(subscription)
            await db.flush()

        subscription.product_id = renewal.productId
        subscription.is_active = is_active
        subscription.auto_renew = auto_renew
        subscription.start_at = started_at
        subscription.end_at = expired_at
        subscription.apple_original_transaction_id = transaction.originalTransactionId
        subscription.apple_latest_transaction_id = transaction.transactionId
        subscription.updated_at = datetime.now(timezone.utc)

        db.add(SubscriptionEvent(
            user_id=user.id,
            subscription_id=subscription.id,
            event_type=_subscription_event_type(notification.rawNotificationType, auto_renew),
            payload={"signed_payload": signed_payload},
            note=notification.rawNotificationType,
            notification_uuid=notification_uuid,
        ))
    return True

async def query_subscription_status_service(
    db: AsyncSession,
    user_id: str,
    info: SubscriptionQueryInfo
) -> SubscriptionStatusResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        
        if info.enforce:
            user_apple_original_transaction_id = user.subscription_info.apple_original_transaction_id if user.subscription_info else None
            tid_need_to_query = info.transaction_id if info.transaction_id else user_apple_original_transaction_id
            if tid_need_to_query:
                transaction, transaction_payload, renew_payload = await query_user_subscroption_status(tid_need_to_query)
                if not transaction_payload or not renew_payload or not transaction:
                    # 订单查询异常
                    logger.error(f"订单查询异常 {tid_need_to_query}")
                    if user.subscription_info:
                        user.subscription_info.is_active = False
                        user.subscription_info.auto_renew = False
                    return SubscriptionStatusResponse(
                        is_active=user.subscription_info.is_active if user.subscription_info else False,
                        auto_renew=user.subscription_info.auto_renew if user.subscription_info else None, 
                        started_at=user.subscription_info.start_at.isoformat() if user.subscription_info and user.subscription_info.start_at else None,
                        expired_at=user.subscription_info.end_at.isoformat() if user.subscription_info and user.subscription_info.end_at else None
                    )
                if transaction_payload.appAccountToken == str(user.apple_iap_token):
                    is_active = (transaction.status == 1 or transaction.status == 4)
                    auto_renew = renew_payload.autoRenewStatus == 1
                    started_at = (
                        datetime.fromtimestamp(renew_payload.recentSubscriptionStartDate / 1000, tz=timezone.utc)
                        if renew_payload.recentSubscriptionStartDate
                        else None
                    )
                    expired_at = (
                        datetime.fromtimestamp(transaction_payload.expiresDate / 1000, tz=timezone.utc)
                        if transaction_payload.expiresDate
                        else None
                    )
                    if user.subscription_info:
                        user.subscription_info.product_id = renew_payload.productId
                        user.subscription_info.is_active = is_active
                        user.subscription_info.auto_renew = auto_renew
                        user.subscription_info.start_at = started_at
                        user.subscription_info.end_at = expired_at
                        user.subscription_info.apple_original_transaction_id = renew_payload.originalTransactionId
                        user.subscription_info.apple_latest_transaction_id = transaction_payload.transactionId
                        # 强制更新 updated_at
                        user.subscription_info.updated_at = datetime.now(timezone.utc)
                    else:
                        new_subs_info = UserSubscription(
                            user_id=user.id,
                            product_id=renew_payload.productId,
                            is_active = is_active,
                            auto_renew = auto_renew,
                            start_at = started_at,
                            end_at = expired_at,
                            apple_original_transaction_id = renew_payload.originalTransactionId,
                            apple_latest_transaction_id = transaction_payload.transactionId
                        )
                        db.add(new_subs_info)
                    return SubscriptionStatusResponse(
                        is_active=is_active,
                        auto_renew=auto_renew,
                        started_at=started_at.isoformat() if started_at else None,
                        expired_at=expired_at.isoformat() if expired_at else None,
                    )

        return SubscriptionStatusResponse(
            is_active=user.subscription_info.is_active if user.subscription_info else False,
            auto_renew=user.subscription_info.auto_renew if user.subscription_info else None, 
            started_at=user.subscription_info.start_at.isoformat() if user.subscription_info and user.subscription_info.start_at else None,
            expired_at=user.subscription_info.end_at.isoformat() if user.subscription_info and user.subscription_info.end_at else None
        )


async def query_subscription_account_service(
    db: AsyncSession,
    user_id: str,
    transaction_id: str
) -> str | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    transaction, transaction_payload, renew_payload = await query_user_subscroption_status(transaction_id)
    if not transaction_payload or not renew_payload or not transaction:
        return None
    if transaction.status != 1 and transaction.status != 4:
        return None
    if str(user.apple_iap_token) == transaction_payload.appAccountToken:
        return user.nickname
    if transaction_payload.appAccountToken:
        entitlement_user = await get_user_by_iap_token(db, transaction_payload.appAccountToken)
        return entitlement_user.nickname if entitlement_user else None
    else:
        return None


async def verify_auto_subscription_transaction_service(
    db: AsyncSession,
    user_id: str,
    transaction_id: str
) -> SubscriptionStatusResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        is_active = user.subscription_info.is_active if user.subscription_info else False
        auto_renew = user.subscription_info.auto_renew if user.subscription_info else None
        started_at = user.subscription_info.start_at if user.subscription_info else None
        expired_at = user.subscription_info.end_at if user.subscription_info else None
        transaction, transaction_payload, renew_payload = await query_user_subscroption_status(transaction_id)
        if not transaction_payload or not renew_payload or not transaction:
            raise BizException(code=ErrorCode.IAP_ERROR, message="iap_subscription.verify_failed.purchase")
        if transaction_payload.appAccountToken == str(user.apple_iap_token):
            is_active = (transaction.status == 1 or transaction.status == 4)
            auto_renew = renew_payload.autoRenewStatus == 1
            started_at = (
                datetime.fromtimestamp(renew_payload.recentSubscriptionStartDate / 1000, tz=timezone.utc)
                if renew_payload.recentSubscriptionStartDate
                else None
            )
            expired_at = (
                datetime.fromtimestamp(transaction_payload.expiresDate / 1000, tz=timezone.utc)
                if transaction_payload.expiresDate
                else None
            )
            if user.subscription_info:
                user.subscription_info.product_id = renew_payload.productId
                user.subscription_info.is_active = is_active
                user.subscription_info.auto_renew = auto_renew
                user.subscription_info.start_at = started_at
                user.subscription_info.end_at = expired_at
                user.subscription_info.apple_original_transaction_id = renew_payload.originalTransactionId
                user.subscription_info.apple_latest_transaction_id = transaction_payload.transactionId
                # 强制更新 updated_at
                user.subscription_info.updated_at = datetime.now(timezone.utc)
            else:
                new_subs_info = UserSubscription(
                    user_id=user.id,
                    product_id=renew_payload.productId,
                    is_active = is_active,
                    auto_renew = auto_renew,
                    start_at = started_at,
                    end_at = expired_at,
                    apple_original_transaction_id = renew_payload.originalTransactionId,
                    apple_latest_transaction_id = transaction_payload.transactionId
                )
                db.add(new_subs_info)
        else:
            raise BizException(code=ErrorCode.IAP_ERROR, message="iap_subscription.verify_failed.purchase")
        return SubscriptionStatusResponse(
            is_active=is_active,
            auto_renew=auto_renew,
            started_at=started_at.isoformat() if started_at else None,
            expired_at=expired_at.isoformat() if expired_at else None,
        )


async def verify_coupon_transaction_service(
    db: AsyncSession,
    user_id: str,
    jws: str
) -> int:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        payload = await verify_and_decode_transaction_service(jws)
        if payload is None:
            raise BizException(code=ErrorCode.IAP_ERROR, message="iap_coupon.verify_failed.purchase")
        transaction = CouponRechargeTransaction(
            user_id=user.id,
            product_id=payload.productId,
            original_transaction_id=payload.originalTransactionId,
            quantity=payload.quantity,
            type=payload.type,
            app_account_token=payload.appAccountToken,
            price=payload.price
        )
        db.add(transaction)
        if payload.productId is None or payload.quantity != 1 or payload.rawType != "Consumable" or payload.appAccountToken != str(user.apple_iap_token):
            raise BizException(code=ErrorCode.IAP_ERROR, message="iap_coupon.verify_failed.purchase")
        coupon_price = await get_coupon_price(db, payload.productId)
        if coupon_price is None:
            raise BizException(code=ErrorCode.IAP_ERROR, message="iap_coupon.verify_failed.purchase")
        gift_coupon = coupon_price.gift_price or 0
        coupon_balance = await reward_ccasset(db, CCAssetType.COUPON, coupon_price.price + gift_coupon, user.id, f"充值点券：{coupon_price.price} 赠送：{gift_coupon}", AssetOperation.RECHARGE)
        return coupon_balance

async def query_coupon_shop_infos_service(
    db: AsyncSession,
    user_id: str
) -> CouponShopResponse:
    coupons = await get_coupon_prices_all(db)
    return CouponShopResponse(
        coupons= [CouponShopInfo(
            product_id=coupon.product_id,
            coupon=coupon.price,
            coupon_gift=coupon.gift_price
        ) for coupon in coupons]
    )
