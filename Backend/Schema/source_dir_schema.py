from pydantic import BaseModel

class RoutePathPayload(BaseModel):
    path: str
