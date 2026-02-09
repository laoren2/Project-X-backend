from app.db.models.asset import CouponRechargeTransaction
from app.db.models.user import User, UserSubscription
from app.core.errors import ErrorCode
from app.core.config import settings
from app.schemas.base import BizException
from app.schemas.user import SubscriptionStatusResponse, SubscriptionQueryInfo
from app.schemas.asset import AssetOperation, CouponShopResponse, CouponShopInfo
from app.schemas.common import CCAssetType
from app.crud.user import get_user_by_id, get_user_by_iap_token
from app.crud.asset_manage import get_coupon_prices_all, reward_ccasset, get_coupon_price
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.services.app_store_api_tool import query_user_subscroption_status, verify_and_decode_transaction_service
import uuid, random, math, json, os, logging

logger = logging.getLogger(__name__)

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
                        datetime.fromtimestamp(renew_payload.renewalDate / 1000, tz=timezone.utc)
                        if renew_payload.renewalDate
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
                datetime.fromtimestamp(renew_payload.renewalDate / 1000, tz=timezone.utc)
                if renew_payload.renewalDate
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
