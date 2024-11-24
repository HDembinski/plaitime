from pathlib import Path

BASE_DIRECTORY = Path.home() / ".plaitime"
BASE_DIRECTORY.mkdir(exist_ok=True)
SETTINGS_FILE_NAME = BASE_DIRECTORY / "settings.json"
SESSION_DIRECTORY = BASE_DIRECTORY / "sessions"
SESSION_DIRECTORY.mkdir(exist_ok=True)
MEMORY_DIRECTORY = BASE_DIRECTORY / "memories"
MEMORY_DIRECTORY.mkdir(exist_ok=True)

CHARACTERS_PER_TOKEN = 4  # on average

STORY_PROMPT = """Given a summary in `<summary>` tags and a chat in `<chat>` tags, please extend the summary with new paragraphs.

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

CHARACTERS_PROMPT = """Analyze the chat within `<chat>` tags and extract key information about characters.

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
            "appearance": "visual description of the character, for example, skin color, handsome or ugly, thin or thick, etc.",
            "clothing": "description of clothing",
            "occupation": "occupation of the character and/or role in the story",
            "weapons": "description of weapons, if any",
            "abilities": "descriptions of abilities",
            "notes": "notes that do not fit into the previous categories"
        }}
    ]
}}
"""

LOCATIONS_PROMPT = """Analyze the chat within `<chat>` tags and extract key information about locations.

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

WORLD_PROMPT = """Analyze the chat within `<chat>` tags and extract key information from the story.
    
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
