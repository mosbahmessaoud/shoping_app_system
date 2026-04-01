from pydantic import BaseModel


class UserTypeRequest(BaseModel):
    email: str


class UserTypeResponse(BaseModel):
    user_type: str
    exists: bool
