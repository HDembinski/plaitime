from pathlib import Path

BASE_DIRECTORY = Path.home() / ".plaitime"
BASE_DIRECTORY.mkdir(exist_ok=True)

CONFIG_FILE_NAME = BASE_DIRECTORY / "config.json"
CHARACTER_DIRECTORY = BASE_DIRECTORY / "characters"
CHARACTER_DIRECTORY.mkdir(exist_ok=True)
MEMORY_DIRECTORY = BASE_DIRECTORY / "memories"
MEMORY_DIRECTORY.mkdir(exist_ok=True)

CHARACTERS_PER_TOKEN = 4  # on average
CONTEXT_MARGIN_FRACTION = 1 / 8

STORY_EXTRACTION_PROMPT = """
**Story Summary Expert**

Analyze the text within `<text>` tags and extract key information from the story.

<text>
{0}
</text>

**Task Requirements**

Extract essential details from the provided narrative, focusing on long-term significance rather than transient information.
Address the entire text, not just the latest events.

**Questions to Answer**

1. **Characters** List all characters mentioned in the story, either directly or indirectly.

2. **Character Descriptions**
	* Age of the character
	* Physical appearance (face, body, visual details)
	* Attire and dress code
	* Occupation or role
	* Distinct traits setting them apart
	* Relevant backstory information

3. **Character Relationships**
	* Nature of their connection (friends, enemies, romantic, etc.)
	* One-sided relationships, if applicable
	* Familiarity and duration of their acquaintance
	* Shared history or significant events they've experienced together

4. **World-Building**
	* Timeframe (era, period, specific date)
	* Genre and tone (adventure, horror, mystery, fantasy, etc.)
	* Locations visited in the story with brief descriptions

**Response Format**

Return extracted facts in Markdown format:

**Summary of the Story**
A concise summary of the narrative appears here.

**Character Descriptions**
- Character 1
  - [Description information]
- Character 2
  - [Description information]
- ...

**Character Relationships**
- Character 1 and 2: [Relationship description]
- ...

**World-Building**
- Genre & Tone: ...
- Realm and Timeframe: ... 
- **Important locations**
  - Place 1: ...
  - Place 2: ...
  - ...
"""
