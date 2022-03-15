from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    ResultUser,
    RoomInfo,
    RoomWaitResponse,
    SafeUser,
    get_user_by_token,
)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)
    # print(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # print(req)
    model.update_user(token, req.user_name, req.leader_card_id)
    return Empty()


class PlayInfo(BaseModel):
    live_id: int
    select_difficulty: LiveDifficulty = LiveDifficulty.normal

    class Config:
        orm_mode = True


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: PlayInfo, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        room_id: int = model.room_create(
            user_id=user.id,
            live_id=req.live_id,
            select_difficulty=req.select_difficulty,
        )
        print(room_id)
    return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponse(BaseModel):
    room_info_list: list[RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest):
    room_ids: list[RoomInfo] = model.room_list(live_id=req.live_id)
    return RoomListResponse(room_info_list=room_ids)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty = LiveDifficulty.normal


class RoomJoinResponse(BaseModel):
    join_room_result: JoinRoomResult


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)) -> Any:
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        return RoomJoinResponse(
            join_room_result=model.room_join(
                room_id=req.room_id,
                user_id=user.id,
                select_difficulty=req.select_difficulty,
            )
        )


class RoomWaitRequest(BaseModel):
    room_id: int


@app.post("/room/wait", response_model=RoomWaitResponse)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        return model.room_wait(room_id=req.room_id, user_id=user.id)


class RoomStartRequest(BaseModel):
    room_id: int


@app.post("/room/start", response_model=Empty)
def room_start(req: RoomStartRequest, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        model.room_start(room_id=req.room_id, user_id=user.id)
        return Empty()


class RoomEndRequest(BaseModel):
    room_id: int
    judge_count_list: list[int]
    score: int


@app.post("/room/end", response_model=Empty)
def room_end(req: RoomEndRequest, token: str = Depends(get_auth_token)) -> Empty:
    user = get_user_by_token(token=token)
    if user is None:
        return Empty()
    else:
        model.room_end(
            room_id=req.room_id,
            user_id=user.id,
            judge_count_list=req.judge_count_list,
            score=req.score,
        )
        return Empty()


class RoomResultRequest(BaseModel):
    room_id: int


class RoomResultResponse(BaseModel):
    result_user_list: Optional[list[ResultUser]]


@app.post("/room/result", response_model=RoomResultResponse)
def room_result(req: RoomResultRequest, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        return RoomResultResponse(result_user_list=model.room_result(room_id=req.room_id))


class RoomLeaveRequest(BaseModel):
    room_id: int


@app.post("/room/leave", response_model=Empty)
def room_leave(req: RoomLeaveRequest, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        model.room_leave(room_id=req.room_id, user_id=user.id)
        return Empty()
