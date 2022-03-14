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
          "WHERE token = :token"
      ),
      {"token": token}
  )
  try:
    row = result.one()
  except NoResultFound:
    return None
  return SafeUser.from_orm(row)


def _get_user_by_id(conn, id: int) -> Optional[SafeUser]:
  result = conn.execute(
      text(
          "SELECT id, name, leader_card_id FROM user "
          "WHERE id = :id"
      ),
      {"id": id}
  )
  try:
    user = result.one()
  except NoResultFound:
    return None
  return SafeUser.from_orm(user)


def get_user_by_token(token: str) -> Optional[SafeUser]:
  with engine.begin() as conn:
    return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
  with engine.begin() as conn:
    conn.execute(
        text(
            "UPDATE user SET name=:name, leader_card_id = :leader_card_id "
            "WHERE token = :token"
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


class RoomStatus(BaseModel):
  status: WaitRoomStatus
  room_user_list: list[RoomUser]


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
  judge_count_list: Optional[str]
  score: Optional[int]

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
        text(
            "SELECT * FROM room "
            "WHERE wait_room_status = :waiting"
        ),
        {"waiting": WaitRoomStatus.Waiting.value}
    )
  else:
    result = conn.execute(
        text(
            "SELECT * FROM room "
            "WHERE live_id = :live_id AND wait_room_status = :waiting"
        ),
        {"live_id": live_id, "waiting": WaitRoomStatus.Waiting.value}
    )

  rooms = list[Room]()
  for row in result:
    rooms.append(Room.from_orm(row))
  return rooms


def _get_room_members_count_by_room_id(conn, room_id: int) -> int:
  result = conn.execute(
      text(
          "SELECT COUNT(*) FROM room_member "
          "WHERE room_id = :room_id"
      ),
      {"room_id": room_id}
  )
  return result.scalar()


def get_rooms(live_id: int) -> list[RoomInfo]:
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
          "WHERE id = :id"
      ),
      {"id": room_id}
  )
  try:
    room = result.one()
  except NoResultFound:
    return None
  return Room.from_orm(room)


def _get_room_members_count_by_room_id_with_tx(conn, room_id: int) -> int:
  result = conn.execute(
      text(
          "SELECT COUNT(*) FROM room_member "
          "WHERE room_id = :room_id "
          "FOR UPDATE"
      ),
      {"room_id": room_id}
  )
  return result.scalar()


def add_member(
        room_id,
        member_id,
        select_difficulty: LiveDifficulty
) -> JoinRoomResult:
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      return JoinRoomResult.OtherError
    if room.wait_room_status != WaitRoomStatus.Waiting:
      return JoinRoomResult.Disbanded
    if room.owner_id == member_id:
      return JoinRoomResult.OtherError

    membersCount = _get_room_members_count_by_room_id_with_tx(conn, room_id)
    if membersCount >= MAX_USER_COUNT:
      return JoinRoomResult.RoomFull

    _create_member(conn, room_id, member_id, select_difficulty)
  return JoinRoomResult.OK


def _get_members_by_room_id(conn, room_id: int) -> list[RoomMember]:
  result = conn.execute(
      text(
          "SELECT * FROM room_member "
          "WHERE room_id = :room_id"
      ),
      {"room_id": room_id}
  )

  members = list[RoomMember]()
  for row in result:
    members.append(RoomMember.from_orm(row))
  return members


def get_room_status(user_id: int, room_id: int) -> Optional[RoomStatus]:
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      return None

    userList = list[RoomUser]()
    members = _get_members_by_room_id(conn, room_id)
    for member in members:
      userInfo = _get_user_by_id(conn, member.member_id)
      if userInfo is None:
        return None

      userList.append(
          RoomUser(
              user_id=member.member_id,
              name=userInfo.name,
              leader_card_id=userInfo.leader_card_id,
              select_difficulty=member.live_difficulty,
              is_me=member.member_id == user_id,
              is_host=member.member_id == room.owner_id
          )
      )

  return RoomStatus(status=room.wait_room_status, room_user_list=userList)


def _update_room_status(conn, room_id: int, status: WaitRoomStatus):
  conn.execute(
      text(
          "UPDATE room "
          "SET wait_room_status = :status "
          "WHERE id = :id"
      ),
      {"id": room_id, "status": status.value}
  )


def start_game(user_id: int, room_id: int):
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      raise HTTPException(status_code=404)
    if room.owner_id != user_id:
      raise HTTPException(status_code=403, detail="you are not the owner")
    if room.wait_room_status != WaitRoomStatus.Waiting:
      raise HTTPException(status_code=400, detail="room is already started")

    _update_room_status(conn, room_id, WaitRoomStatus.LiveStart)


def _update_result(
        conn,
        user_id: int,
        room_id: int,
        judge_count_list: list[int],
        score: int
):
  judgeCountListStr = ",".join(map(str, judge_count_list))

  conn.execute(
      text(
          "UPDATE room_member "
          "SET judge_count_list = :judge_count_list, score = :score "
          "WHERE room_id = :room_id AND member_id = :member_id"
      ),
      {
          "judge_count_list": judgeCountListStr,
          "score": score,
          "room_id": room_id,
          "member_id": user_id
      }
  )


def finish_game(
    user_id: int,
    room_id: int,
    judge_count_list: list[int],
    score: int
):
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      raise HTTPException(status_code=404)
    if room.wait_room_status == WaitRoomStatus.Waiting:
      raise HTTPException(status_code=400, detail="room is not started")

    _update_room_status(conn, room_id, WaitRoomStatus.Dissolution)
    _update_result(conn, user_id, room_id, judge_count_list, score)


def _get_results_by_room_id(conn, room_id: int) -> list[ResultUser]:
  result = conn.execute(
      text(
          "SELECT * FROM room_member "
          "WHERE room_id = :room_id "
          "AND judge_count_list IS NOT NULL AND score IS NOT NULL"
      ),
      {"room_id": room_id}
  )

  members = list[ResultUser]()
  for row in result:
    member = RoomMember.from_orm(row)
    judgeCountStrList = member.judge_count_list.split(",")
    judgeCountList = [int(s) for s in judgeCountStrList]
    members.append(ResultUser(
        user_id=member.member_id,
        judge_count_list=judgeCountList,
        score=member.score
    ))
  return members


def get_results(room_id: int) -> list[ResultUser]:
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      raise HTTPException(status_code=404)
    if room.wait_room_status != WaitRoomStatus.Dissolution:
      raise HTTPException(status_code=400, detail="room is not ended")

    return _get_results_by_room_id(conn, room_id)


def _delete_member(conn, room_id: int, member_id: int):
  conn.execute(
      text(
          "DELETE FROM room_member "
          "WHERE room_id = :room_id AND member_id = :member_id"
      ),
      {"room_id": room_id, "member_id": member_id}
  )


def _update_room_owner(conn, id: int, owner_id: int):
  conn.execute(
      text(
          "UPDATE room "
          "SET owner_id = :owner_id"
          "WHERE id = :id"
      ),
      {"id": id, "owner_id": owner_id}
  )


def delete_member(room_id: int, member_id: int):
  with engine.begin() as conn:
    room = _get_room_by_id(conn, room_id)
    if room is None:
      raise HTTPException(status_code=404)
    if room.wait_room_status != WaitRoomStatus.Waiting:
      raise HTTPException(status_code=400, detail="room is already started")

    members = _get_members_by_room_id(conn, room_id)
    if all(member.member_id != member_id for member in members):
      raise HTTPException(
          status_code=404,
          detail="member is not found in the room"
      )

    _delete_member(conn, room_id, member_id)
    if len(members) <= 1:
      _update_room_status(conn, room_id, WaitRoomStatus.Dissolution)
      return
    if room.owner_id == member_id:
      for member in members:
        if member.member_id != member_id:
          _update_room_owner(conn, room_id, member.member_id)
          break
