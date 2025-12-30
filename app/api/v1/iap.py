from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_user, get_language
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext, SubscriptionStatusResponse, IAPJWSRequest, IAPTransactionRequest
from app.schemas.asset import CouponShopResponse
from app.services.iap import (
    verify_auto_subscription_transaction_service, verify_coupon_transaction_service,
    query_subscription_status_service, query_subscription_account_service,
    query_coupon_shop_infos_service
)

router = APIRouter(dependencies=[Depends(get_language)])


# 查询用户订阅状态
@router.get("/query_subscription_status",response_model=BaseResponse[SubscriptionStatusResponse],summary="查询用户订阅状态")
async def query_subscription_status(
    enforce: bool = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_subscription_status_service(db, auth.payload["user_id"], enforce)
    return BaseResponse.success(token=auth.new_token, data=result, message="success")


# 校验自动续费订阅交易
@router.post("/verify_auto_subscription_transaction",response_model=BaseResponse[SubscriptionStatusResponse],summary="验证自动续费订阅的交易")
async def verify_auto_subscription(
    transaction: IAPTransactionRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await verify_auto_subscription_transaction_service(db, auth.payload["user_id"], transaction.transaction_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="success")

# 校验点券交易
@router.post("/verify_coupon_transaction",response_model=BaseResponse[int],summary="验证点券的交易")
async def verify_coupon_transaction(
    transaction: IAPJWSRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await verify_coupon_transaction_service(db, auth.payload["user_id"], transaction.jws)
    return BaseResponse.success(token=auth.new_token, data=result, message="success")

# 查询当前 appleID 下自动续费订阅交易的账号昵称
@router.post("/query_subscription_account",response_model=BaseResponse[str | None],summary="查询当前 appleID 下自动续费订阅交易的账号昵称")
async def query_subscription_account(
    transaction: IAPTransactionRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_subscription_account_service(db, auth.payload["user_id"], transaction.transaction_id)
    return BaseResponse.success(token=auth.new_token, data=result, message="success")

# 查询点券商店信息
@router.get("/query_coupon_infos",response_model=BaseResponse[CouponShopResponse],summary="查询点券商店信息")
async def query_coupon_infos(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_coupon_shop_infos_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result, message="success")