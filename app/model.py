import json
import uuid
from enum import IntEnum
from typing import Optional

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
    conn.execute(
        text(
            "INSERT INTO user "
            "(name, token, leader_card_id) "
            "VALUES (:name, :token, :leader_card_id)"
        ),
        {"name": name, "token": token, "leader_card_id": leader_card_id}
    )
  return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
  result = conn.execute(
      text(
          "SELECT id, name, leader_card_id FROM user "
          "WHERE token=:token"
      ),
      {"token": token}
  )
  try:
    row = result.one()
  except NoResultFound:
    return None
  return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
  with engine.begin() as conn:
    return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
  with engine.begin() as conn:
    conn.execute(
        text(
            "UPDATE user SET name=:name, leader_card_id=:leader_card_id "
            "WHERE token=:token"
        ),
        {"name": name, "leader_card_id": leader_card_id, "token": token}
    )


class LiveDifficulty(IntEnum):
  normal = 1
  hard = 2


class JoinRoomResult(IntEnum):
  OK = 1
  RoomFull = 2
  Disbanded = 3
  OtherError = 4


class WaitRoomStatus(IntEnum):
  Waiting = 1
  LiveStart = 2
  Dissolution = 3


class RoomInfo(BaseModel):
  room_id: int
  live_id: int
  joined_user_count: int
  max_user_count: int


class RoomUser(BaseModel):
  user_id: int
  name: str
  leader_card_id: int
  select_difficulty: LiveDifficulty
  is_me: bool
  is_host: bool


class ResultUser(BaseModel):
  user_id: int
  judge_count_list: list[int]
  score: int


class Room(BaseModel):
  id: int
  live_id: int
  owner_id: int
  wait_room_status: WaitRoomStatus

  class Config:
    orm_mode = True


class RoomMember(BaseModel):
  room_id: int
  member_id: int
  live_difficulty: LiveDifficulty

  class Config:
    orm_mode = True
