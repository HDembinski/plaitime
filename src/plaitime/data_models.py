from pydantic import BaseModel
from typing import Annotated
from annotated_types import Interval
from PySide6 import QtGui

# Metadata tags
LongString = Annotated[str, "long"]
ModelString = Annotated[str, "model"]
FontString = Annotated[str, "font"]
ColorString = Annotated[str, "color"]


class Session(BaseModel):
    name: str = "Assistant"
    prompt: LongString = ""
    model: ModelString = "llama3.2:latest"
    temperature: Annotated[float, Interval(ge=0, le=2)] = 0.7
    extraction_model: ModelString = "llama3.2:latest"
    extraction_temperature: Annotated[float, Interval(ge=0, le=2)] = 0.1
    save_conversation: bool = True


class Message(BaseModel):
    role: str
    content: str


class Character(BaseModel):
    name: str
    eyes: str = ""
    hair: str = ""
    age: str = ""
    appearance: str = ""
    clothing: str = ""
    occupation: str = ""
    weapons: LongString = ""
    abilities: LongString = ""
    notes: LongString = ""


class Location(BaseModel):
    name: str
    description: str
    notes: str


class CharacterList(BaseModel):
    characters: list[Character] = []


class LocationList(BaseModel):
    locations: list[Location] = []


class Memory(CharacterList, LocationList):
    messages: list[Message] = []
    story: LongString = ""
    world: LongString = ""


class Colors(BaseModel):
    user: ColorString = "#f8f8f8"
    assistant: ColorString = "#e6f5ff"
    em: ColorString = "#034f84"


class Font(BaseModel):
    family: FontString = "Arial"
    size: Annotated[int, Interval(ge=1, le=100)] = 11

    def qfont(self):
        return QtGui.QFont(self.family, self.size)


class Settings(BaseModel):
    session: Annotated[str, "noconfig"] = ""
    geometry: Annotated[tuple[int, int, int, int], "noconfig"] = (100, 100, 600, 600)
    font: Font = Font()
    colors: Colors = Colors()
    llm_timeout: str = "1h"
    context_margin_fraction: Annotated[int, Interval(ge=0, le=100)] = 15
