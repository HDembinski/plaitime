from pydantic import BaseModel
from typing import Annotated
from annotated_types import Interval
from . import USER_COLOR, ASSISTANT_COLOR, EM_COLOR


# Metadata tags
ShortString = Annotated[str, "short"]
LongString = Annotated[str, "long"]
ModelString = Annotated[str, "model"]
Color = Annotated[str, "color"]


class Character(BaseModel):
    name: ShortString = "Assistant"
    prompt: LongString = ""
    model: ModelString = "llama3.2:latest"
    temperature: Annotated[float, Interval(ge=0, le=2)] = 0.7
    save_conversation: bool = True


class Message(BaseModel):
    role: str
    content: str


class Memory(BaseModel):
    messages: list[Message] = []
    memories: list[str] = []


class Settings(BaseModel):
    character: Annotated[str, "noconfig"] = ""
    geometry: Annotated[tuple[int, int, int, int], "noconfig"] = (100, 100, 600, 600)
    user_color: Color = USER_COLOR
    assistant_color: Color = ASSISTANT_COLOR
    em_color: Color = EM_COLOR
