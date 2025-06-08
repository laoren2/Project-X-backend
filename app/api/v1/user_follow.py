from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.user_follow import get_following_list, get_follower_list, get_friend_list, follow_user, cancel_follow_user, get_relationship_service, get_relation_count
from app.schemas.user_follow import RelationListResponse, PersonInfoResponse
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext, UserRelationInfo, RelationshipStatus
import uuid


router = APIRouter()

@router.get("/relationship", response_model=BaseResponse[RelationshipStatus], summary="关注某用户")
async def get_relationship(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext=Depends(get_current_user)
):
    relationship = await get_relationship_service(db, auth.payload["user_id"], user_id)
    return BaseResponse.success(token=auth.new_token, message="查询关系成功", data=relationship)


@router.get("/relation_info", response_model=BaseResponse[UserRelationInfo], summary="获取某用户的各关系数量")
async def get_relation_info(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    relation_info = await get_relation_count(db, user_id)
    return BaseResponse.success(message="查询各关系数量成功", data=relation_info)


@router.post("/follow", response_model=BaseResponse[RelationshipStatus], summary="关注某用户")
async def following(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext=Depends(get_current_user)
):
    await follow_user(db, auth.payload["user_id"], user_id)
    relationship = await get_relationship_service(db, auth.payload["user_id"], user_id)
    return BaseResponse.success(token=auth.new_token, message="关注成功", data=relationship)


@router.post("/cancel_follow", response_model=BaseResponse[RelationshipStatus], summary="取消关注某用户")
async def cancel_following(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext=Depends(get_current_user)
):
    await cancel_follow_user(db, auth.payload["user_id"], user_id)
    relationship = await get_relationship_service(db, auth.payload["user_id"], user_id)
    return BaseResponse.success(token=auth.new_token, message="取消关注成功", data=relationship)


@router.get("/following_list", response_model=BaseResponse[RelationListResponse], summary="获取用户的关注列表")
async def get_following(
    user_id: str,
    limit: int = Query(20, le=100),
    cursor_created_at: Optional[datetime] = Query(None),
    cursor_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    users, next_cursor_created_at, next_cursor_id, has_more = await get_following_list(db, user_id, limit=limit, cursor_created_at=cursor_created_at, cursor_id=cursor_id, search=search)
    return BaseResponse.success(message="成功获取关注列表", data=RelationListResponse(
        users=users,
        next_cursor_created_at=next_cursor_created_at,
        next_cursor_id=next_cursor_id,
        has_more=has_more
    ))

@router.get("/follower_list", response_model=BaseResponse[RelationListResponse], summary="获取用户的粉丝列表")
async def get_follower(
    user_id: str,
    limit: int = Query(20, le=100),
    cursor_created_at: Optional[datetime] = Query(None),
    cursor_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    users, next_cursor_created_at, next_cursor_id, has_more = await get_follower_list(db, user_id, limit=limit, cursor_created_at=cursor_created_at, cursor_id=cursor_id, search=search)
    return BaseResponse.success(message="成功获取粉丝列表", data=RelationListResponse(
        users=users,
        next_cursor_created_at=next_cursor_created_at,
        next_cursor_id=next_cursor_id,
        has_more=has_more
    ))

@router.get("/friend_list", response_model=BaseResponse[RelationListResponse], summary="获取用户的朋友列表")
async def get_friend(
    user_id: str,
    limit: int = Query(20, le=100),
    cursor_created_at: Optional[datetime] = Query(None),
    cursor_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    users, next_cursor_created_at, next_cursor_id, has_more = await get_friend_list(db, user_id, limit=limit, cursor_created_at=cursor_created_at, cursor_id=cursor_id, search=search)
    return BaseResponse.success(message="成功获取朋友列表", data=RelationListResponse(
        users=users,
        next_cursor_created_at=next_cursor_created_at,
        next_cursor_id=next_cursor_id,
        has_more=has_more
    ))
