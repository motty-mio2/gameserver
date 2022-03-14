import json
import uuid
from enum import IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


class LiveDifficulty(IntEnum):
    normal = 1
    hard = 2
class WaitRoomStatus(IntEnum):
    Waiting = 1  # ホストがライブ開始ボタン押すのを待っている
    LiveStart = 2  # ライブ画面遷移OK
    Dissolution = 3  # 解散された
class JoinInfo(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty = LiveDifficulty.normal

class RoomInfo(BaseModel):
    name: type  # memo
    room_id: int  # 部屋識別子
    live_id: int  # プレイ対象の楽曲識別子
    room_members_count: int  # 部屋に入っている人数
    max_user_count: int  # 部屋の最大人数


def _get_room_info(room_id: int) -> RoomInfo:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT `live_id`,`room_members_count`,`max_user_count` FROM `room` WHERE `room_id`=:room_id"),
            {"room_id": room_id},
        )
        room_info: list[int] = result.fetchall()[0]
        return RoomInfo(
            room_id=room_id, live_id=room_info[0], room_members_count=room_info[1], max_user_count=room_info[2]
        )


class RoomUser(BaseModel):
    user_id: int  # ユーザー識別子
    name: str  # ユーザー名
    leader_card_id: int  # 設定アバター
    select_difficulty: LiveDifficulty  # 選択難易度
    is_me: bool  # リクエスト投げたユーザーと同じか
    is_host: bool  # 部屋を立てた人か

def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `user` (name, token, leader_card_id) VALUES (:name, :token, :leader_card_id)"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result)
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    # TODO: 実装
    result = conn.execute(text("select * from user"))
    rows = result.fetchall()
    for user in rows:
        if user["token"] == token:
            target_user = SafeUser(id=user["id"], name=user["name"], leader_card_id=user["leader_card_id"])
            return target_user
    else:
        return None


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE `user` SET name=:name, leader_card_id=:leader_card_id WHERE token=:token"),
            {"name": name, "leader_card_id": leader_card_id, "token": token},
        )


def room_create(user_id: int, live_id: int, select_difficulty: LiveDifficulty) -> int:
    with engine.begin() as conn:
        room_id: int = conn.execute(
            text(
                "INSERT INTO `room` (live_id, room_members_count, owner_id) VALUES (:live_id, :room_members_count, :owner_id)"
            ),
            {"live_id": live_id, "room_members_count": 1, "owner_id": user_id},  # type: ignore
        ).lastrowid
        conn.execute(  # type: ignore
            text("INSERT INTO `room_member` (room_id, id) VALUES(:room_id, :id)"),
            {"room_id": room_id, "id": user_id},
        )
        return room_id


def room_list(live_id: int) -> list[int]:
    with engine.begin() as conn:
        result = conn.execute(text("SELECT `room_id` FROM `room` WHERE `live_id`=:live_id"), {"live_id": live_id})
        room_ids = [room[0] for room in result.fetchall()]
    return room_ids


class JoinRoomResult(IntEnum):
    Ok = 1  # 入場OK
    RoomFull = 2  # 満員
    Disbanded = 3  # 解散済み
    OtherError = 4  # その他エラー


def room_join(room_id: int, user_id: int, select_difficulty: LiveDifficulty) -> JoinRoomResult:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT `room_members_count` FROM `room` WHERE `room_id`=:room_id"), {"room_id": room_id}
        )
        members: int = (result.fetchall())[0][0]
        if members == 0:
            return JoinRoomResult.Disbanded
        elif 0 < members < 4:
            # UPDATE room Table
            conn.execute(
                text("UPDATE `room` SET room_members_count=:room_members_count WHERE room_id=:room_id"),
                {"room_members_count": members + 1, "room_id": room_id},
            )
            # UPDATE room_member table
            conn.execute(
                text(
                    "INSERT `room_member` (room_id, live_id, id, diff, exist) \
                    VALUES(:room_id, :token, :leader_card_id, :diff, :exist) \
                    ON DUPLICATE KEY UPDATE (exist) VALUES (:exist)"
                ),
                {"room_id": room_id, "id": user_id, "diff": select_difficulty, "exist": 1},
            )
            return JoinRoomResult.Ok
        else:
            return JoinRoomResult.RoomFull
    return JoinRoomResult.OtherError


def room_wait(room_id: int, user_id: int) -> tuple[Optional[WaitRoomStatus], Optional[list[RoomUser]]]:
    with engine.begin() as conn:
        status, owner_id = conn.execute(
            text("SELECT `status`,`owner_id` FROM `room` WHERE `room_id`=:room_id"), {"room_id": room_id}
        ).fetchall()[0]

        status: WaitRoomStatus = WaitRoomStatus(status)

        result_member: list[tuple[int, ...]] = conn.execute(  # type: ignore
            text("SELECT `id`, `diff`, `exist` FROM `room_member` WHERE `room_id`=:room_id"), {"room_id": room_id}
        ).fetchall()  # type: ignore

        user_ids: dict[int, dict[str, int]] = dict()
        for id, diff, exist in result_member:  # type: ignore
            if id in user_ids.keys():
                user_ids[id]["exist"] *= exist
            else:
                user_ids[id] = {"diff": diff, "exist": exist}

        user_list: list[RoomUser] = []
        for target_id, target_status in user_ids.items():
            if target_status["exist"]:
                name, lci = conn.execute(  # type: ignore
                    text("SELECT `name`, `leader_card_id` FROM `user` WHERE `id`=:user_id"), {"user_id": user_id}
                ).fetchall()[0]
                user_list.append(
                    RoomUser(
                        user_id=target_id,
                        name=name,  # type: ignore
                        leader_card_id=lci,  # type: ignore
                        select_difficulty=LiveDifficulty.normal(target_status["diff"]),  # type: ignore
                        is_me=(target_id == user_id),
                        is_host=(target_id == owner_id),  # type: ignore
                    )
                )
            else:
                pass

    return status, user_list

