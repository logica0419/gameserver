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


MAX_USER_COUNT = 4


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


def _create_room(conn, owner_id: int, live_id: int,) -> int:
  result = conn.execute(
      text(
          "INSERT INTO room "
          "(live_id, owner_id, wait_room_status) "
          "VALUES (:live_id, :owner_id, :wait_room_status)"
      ),
      {
          "live_id": live_id,
          "owner_id": owner_id,
          "wait_room_status": WaitRoomStatus.Waiting.value
      }
  )
  return result.lastrowid


def _create_member(
    conn,
    room_id: int,
    member_id: int,
    select_difficulty: LiveDifficulty
):
  conn.execute(
      text(
          "INSERT INTO room_member "
          "(room_id, member_id, live_difficulty) "
          "VALUES (:room_id, :member_id, :live_difficulty)"
      ),
      {
          "room_id": room_id,
          "member_id": member_id,
          "live_difficulty": select_difficulty.value
      }
  )


def create_room(
        owner_id: int,
        live_id: int,
        select_difficulty: LiveDifficulty
) -> int:
  with engine.begin() as conn:
    room_id = _create_room(conn, owner_id, live_id)
    _create_member(conn, room_id, owner_id, select_difficulty)
  return room_id


def _get_rooms_by_live_id(conn, live_id: int) -> list[Room]:
  if live_id == 0:
    result = conn.execute(
        text("SELECT * FROM room"),
    )
  else:
    result = conn.execute(
        text(
            "SELECT * FROM room "
            "WHERE live_id=:live_id"
        ),
        {"live_id": live_id}
    )

  rooms = list[Room]()
  for row in result:
    rooms.append(Room.from_orm(row))
  return rooms


def _get_room_members_count_by_room_id(conn, room_id: int) -> int:
  result = conn.execute(
      text(
          "SELECT COUNT(*) FROM room_member "
          "WHERE room_id=:room_id"
      ),
      {"room_id": room_id}
  )
  return result.scalar()


def get_rooms_by_live_id(live_id: int) -> list[RoomInfo]:
  roomInfos = list[RoomInfo]()
  with engine.begin() as conn:
    rooms = _get_rooms_by_live_id(conn, live_id)
    for room in rooms:
      memberCount = _get_room_members_count_by_room_id(conn, room.id)
      roomInfos.append(
          RoomInfo(
              room_id=room.id,
              live_id=room.live_id,
              joined_user_count=memberCount,
              max_user_count=MAX_USER_COUNT
          )
      )
  return roomInfos


def _get_room_by_id(conn, room_id: int) -> Optional[Room]:
  result = conn.execute(
      text(
          "SELECT * FROM room "
          "WHERE id=:id"
      ),
      {"id": room_id}
  )
  try:
    room = result.one()
  except NoResultFound:
    return None
  return Room.from_orm(room)


def add_member(
        room_id,
        member_id,
        select_difficulty: LiveDifficulty
) -> JoinRoomResult:
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      return JoinRoomResult.OtherError
    if room.wait_room_status == WaitRoomStatus.Dissolution:
      return JoinRoomResult.Disbanded

    membersCount = _get_room_members_count_by_room_id(conn, room_id)
    if membersCount >= MAX_USER_COUNT:
      return JoinRoomResult.RoomFull

    _create_member(conn, room_id, member_id, select_difficulty)
  return JoinRoomResult.OK
