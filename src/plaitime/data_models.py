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
    characters2: LongString = ""


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
    story_prompt: LongString = """Given a summary in `<summary>` tags and a chat in `<chat>` tags, please extend the summary with new paragraphs.

<summary>
{summary}
</summary>

<chat>
{dialog}
</chat>

# Task Requirements

Continue the summary based on the information provided in the chat.

# Response format

Only return the new paragraphs that should be added to the summary and nothing else, please.
Do not repeat anything that is already covered by the summary and do not rephrase the summary.
"""

    characters_prompt: LongString = """Analyze the chat within `<chat>` tags and extract key information about characters.

<chat>
{dialog}
</chat>

# Task Requirements

Extract essential details about characters mentioned in the provided narrative. Focus on long-term significance rather than transient information.
Give equal attention to the entire chat, not just the last part.

1. List all characters mentioned in the chat, either directly or indirectly.

2. Character descriptions to pay attention to:
    - Name of the character
	- Physical appearance (face, body, visual details)
	- Age of the character
	- Clothing
	- Occupation or role
    - Weapons
    - Abilities
	- Distinct traits setting them apart

# Response Format

Please return the extracted character information in JSON format and assign an empty string ("") to a field if no information is provided in the text:

{{
    "characters": [
        {{
            "name": "name of character",
            "eyes": "description of eyes",
            "hair": "description of hair",
            "age": "(approximate) age of the character",
            "clothing": "description of clothing",
            "occupation": "occupation of the character and/or role in the story",
            "weapons": "description of weapons, if any",
            "abilities": "descriptions of abilities",
            "notes": "notes that do not fit into the previous categories"
        }}
    ]
}}
"""

    locations_prompt: LongString = """Analyze the chat within `<chat>` tags and extract key information about locations.

<chat>
{dialog}
</chat>

# Task Requirements

Extract essential details about all locations mentioned in the provided narrative.
Give equal attention to the entire chat, not just the last part.

# Response Format

Please return the extracted locations in JSON format and assign an empty string ("") to a field if no information is provided in the text:

{{
    "locations": [
        {{
            "name": "name of location",
            "description": "description of location",
            "notes": "notes about the location, for example, its relevance in the story, major events that happened there, etc."
        }}
    ]
}}
"""

    world_prompt: LongString = """Analyze the chat within `<chat>` tags and extract key information from the story.
    
<chat>
{dialog}
</chat>

# Task Requirements

Extract essential details from the provided narrative, focusing on long-term significance rather than transient information.
Give equal attention to the entire text, not just the last part.

Extract information about world-building:

- Realm (real world, fantasy world, or sci-fi world)
- Timeframe (era, period, or specific date)
- Any information about the world in the story and its (physical or magical) laws

# Response Format

Please return the extracted information normal in prose.
"""
