from pydantic import BaseModel
from typing import Annotated
from annotated_types import Interval
from . import USER_COLOR, ASSISTANT_COLOR, EM_COLOR


# Metadata tags
ShortString = Annotated[str, "short"]
LongString = Annotated[str, "long"]
ModelString = Annotated[str, "model"]
FontString = Annotated[str, "font"]
ColorString = Annotated[str, "color"]


class Session(BaseModel):
    name: ShortString = "Assistant"
    prompt: LongString = ""
    model: ModelString = "llama3.2:latest"
    temperature: Annotated[float, Interval(ge=0, le=2)] = 0.7
    save_conversation: bool = True


class Message(BaseModel):
    role: str
    content: str


class Character(BaseModel):
    name: str
    eyes: str
    hair: str
    clothing: str
    weapons: str
    abilities: str
    notes: str


class Memory(BaseModel):
    messages: list[Message] = []
    characters: list[Character] = []
    story: str = ""


class Settings(BaseModel):
    session: Annotated[str, "noconfig"] = ""
    geometry: Annotated[tuple[int, int, int, int], "noconfig"] = (100, 100, 600, 600)
    font: FontString = "Arial"
    font_size: Annotated[int, Interval(ge=1, le=100)] = 11
    user_color: ColorString = USER_COLOR
    assistant_color: ColorString = ASSISTANT_COLOR
    em_color: ColorString = EM_COLOR
