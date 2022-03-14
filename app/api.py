from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinInfo,
    JoinRoomResult,
    PlayInfo,
    RoomInfo,
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
    return None


class RoomCreateResponse(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: PlayInfo, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        room_id: int = model.room_create(user_id=user.id, live_id=req.live_id, select_difficulty=req.select_difficulty)
        print(room_id)
    return RoomCreateResponse(room_id=room_id)


class RoomListResponse(BaseModel):
    room_ids: list[int]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(live_id: int):
    room_ids: list[int] = model.room_list(live_id=live_id)
    return RoomListResponse(room_ids=room_ids)


@app.post("/room/join", response_model=JoinRoomResult)
def room_join(join_info: JoinInfo, token: str = Depends(get_auth_token)) -> Any:
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        return model.room_join(
            room_id=join_info.room_id, user_id=user.id, select_difficulty=join_info.select_difficulty
        )


@app.post("/room/wait", response_model=list[RoomInfo])
def room_wait(room_id: int, token: str = Depends(get_auth_token)):
    user = get_user_by_token(token=token)
    if user is None:
        return None
    else:
        return model.room_wait(room_id=room_id, user_id=user.id)
