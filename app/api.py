from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    RoomInfo,
    RoomStatus,
    SafeUser
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


def get_auth_token(
        cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
  assert cred is not None
  if not cred.credentials:
    raise HTTPException(status_code=401, detail="invalid credential")
  return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=404)
  return user


class Empty(BaseModel):
  pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
  """ユーザー情報更新"""
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  model.update_user(token, req.user_name, req.leader_card_id)
  return Empty()


# Room APIs


class RoomCreateRequest(BaseModel):
  live_id: int
  select_difficulty: LiveDifficulty


class RoomCreateResponse(BaseModel):
  room_id: int


@app.post("/room/create", response_model=RoomCreateResponse)
def room_create(req: RoomCreateRequest, token: str = Depends(get_auth_token)):
  """新規ルーム作成"""
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  room_id = model.create_room(user.id, req.live_id, req.select_difficulty)
  return RoomCreateResponse(room_id=room_id)


class RoomListRequest(BaseModel):
  live_id: int


class RoomListResponse(BaseModel):
  room_info_list: list[RoomInfo]


@app.post("/room/list", response_model=RoomListResponse)
def room_list(req: RoomListRequest, token: str = Depends(get_auth_token)):
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  room_info_list = model.get_rooms_by_live_id(req.live_id)
  return RoomListResponse(room_info_list=room_info_list)


class RoomJoinRequest(BaseModel):
  room_id: int
  select_difficulty: LiveDifficulty


class RoomJoinResponse(BaseModel):
  join_room_result: JoinRoomResult


@app.post("/room/join", response_model=RoomJoinResponse)
def room_join(req: RoomJoinRequest, token: str = Depends(get_auth_token)):
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  join_room_result = model.add_member(
      req.room_id,
      user.id,
      req.select_difficulty
  )
  return RoomJoinResponse(join_room_result=join_room_result)


class RoomWaitRequest(BaseModel):
  room_id: int


@app.post("/room/wait", response_model=RoomStatus)
def room_wait(req: RoomWaitRequest, token: str = Depends(get_auth_token)):
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  roomStatus = model.get_room_status(user.id, req.room_id)
  if roomStatus is None:
    raise HTTPException(status_code=404)
  return roomStatus


class RoomStartRequest(BaseModel):
  room_id: int


@app.post("/room/start", response_model=Empty)
def room_start(req: RoomStartRequest, token: str = Depends(get_auth_token)):
  user = model.get_user_by_token(token)
  if user is None:
    raise HTTPException(status_code=401)

  model.start_room(user.id, req.room_id)
  return Empty()
