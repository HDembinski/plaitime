from pydantic import BaseModel
from typing import Annotated
from annotated_types import Interval
from PySide6 import QtGui

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
    weapons: str = ""
    abilities: str = ""
    notes: str = ""


class Memory(BaseModel):
    messages: list[Message] = []
    characters: list[Character] = []
    story: str = ""
    world: str = ""
    characters2: str = ""


class Settings(BaseModel):
    session: Annotated[str, "noconfig"] = ""
    geometry: Annotated[tuple[int, int, int, int], "noconfig"] = (100, 100, 600, 600)
    font: FontString = "Arial"
    font_size: Annotated[int, Interval(ge=1, le=100)] = 11
    user_color: ColorString = "#f8f8f8"
    assistant_color: ColorString = "#e6f5ff"
    em_color: ColorString = "#034f84"
    llm_timeout: ShortString = "1h"
    context_margin_fraction: Annotated[int, Interval(ge=0, le=100)] = 15
    story_prompt: LongString = """Analyze the text within `<text>` tags and extract a story summary.

<text>
{0}
</text>

# Task Requirements

Extract essential details from the provided narrative, focusing on long-term significance rather than transient information.
Give equal attention to the entire text, not just the last part. Only return the summary.
"""

    characters_prompt: LongString = """Analyze the text within `<text>` tags and extract key information from the story.
    
<text>
{0}
</text>

# Task Requirements

Extract essential details from the provided narrative, focusing on long-term significance rather than transient information.
Give equal attention to the entire text, not just the last part.

1. List all characters mentioned in the story, either directly or indirectly.

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

Return extracted facts in JSON format, leave a field black if no information is provided in the text:

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

    world_prompt: LongString = """Analyze the text within `<text>` tags and extract key information from the story.
    
<text>
{0}
</text>

# Task Requirements

Extract essential details from the provided narrative, focusing on long-term significance rather than transient information.
Give equal attention to the entire text, not just the last part.

Extract information about world-building:

- Realm (real world, fantasy world, or sci-fi world)
- Timeframe (era, period, or specific date)
- Genre (adventure, horror, mystery, fantasy, etc.) and tone (gritty, light-hearted, mature etc.)
- Locations visited in the story with brief descriptions

# Response Format

Return extracted facts in Markdown format:

- Realm: ...
- Timeframe: ... 
- Genre and tone: ...
- Important locations
  - Place 1: ...
  - Place 2: ...
  - ...
"""

    def qfont(self):
        return QtGui.QFont(self.font, self.font_size)
