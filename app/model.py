import json
import uuid
from enum import Enum, IntEnum
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
        result: Any = conn.execute(
            text(
                "INSERT INTO `room` (live_id, room_members_count, owner_id) VALUES (:live_id, :room_members_count, :owner_id)"
            ),
            {"live_id": live_id, "room_members_count": 1, "owner_id": user_id},  # type: ignore
        )
        print(f"room id is {result.lastrowid}")
        return result.lastrowid


def room_list(live_id: int) -> list[int]:
    with engine.begin() as conn:
        result = conn.execute(text("SELECT `room_id` FROM `room` WHERE `live_id`=:live_id"), {"live_id": live_id})
        room_ids = [room[0] for room in result.fetchall()]
    return room_ids

