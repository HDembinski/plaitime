from pathlib import Path

BASE_DIRECTORY = Path.home() / ".plaitime"
BASE_DIRECTORY.mkdir(exist_ok=True)

CONFIG_FILE_NAME = BASE_DIRECTORY / "config.json"
CHARACTER_DIRECTORY = BASE_DIRECTORY / "characters"
CHARACTER_DIRECTORY.mkdir(exist_ok=True)
MEMORY_DIRECTORY = BASE_DIRECTORY / "memories"
MEMORY_DIRECTORY.mkdir(exist_ok=True)

CHARACTERS_PER_TOKEN = 4  # on average
CONTEXT_MARGIN = 512

STORY_EXTRACTION_PROMPT = """
You are a professional author.

Analyze the story excerpt and extract facts from the story, so that another author can continue the story faithfully.
Try to isolate facts which are established and are of long-term importance to continue the story. Ignore transient or fleeting information.

As you are reading the story excerpt, focus on these questions:

* Character descriptions
  - Start by listing all the characters of the story.
  - How old is the character?
  - Physical appearance? (any details about face or body?)
  - How are they dressed?
  - What is their occupation?
  - Unusual mannerisms?
  - What is revealed about their backstory?

* Relationships between characters
  - Are the characters friends or enemies, close or distant?
  - Are they flirting or in love? Is the love one-sided?
  - Do the characters know each other well or not?

* World-building details
  - When does the story happen?
  - Atmosphere & genre?
  - List all places that are visited in the story and give a short description

# Story excerpt

{0}

# Response instructions

Remember: Try to isolate facts which are established and are of long-term importance to continue the story. Ignore transient or fleeting information.

Remember: Your task was to focus on these questions:

* Character descriptions
  - Start by listing all the characters of the story.
  - How old is the character?
  - Physical appearance? (any details about face or body?)
  - How are they dressed?
  - What is their occupation?
  - Unusual mannerisms?
  - What is revealed about their backstory?

* Relationships between characters
  - Are the characters friends or enemies, close or distant?
  - Are they flirting or in love? Is the love one-sided?
  - Do the characters know each other well or not?

* World-building details
  - When does the story happen?
  - Atmosphere & genre?
  - List all places that are visited in the story and give a short description

Return the information concisely in Markdown format:

**Character descriptions**

- Character 1
  - Info about character 1
- Character 2
  - Info about character 2
- ...

**Character relationships**

- Character 1 and 2: their relationship
- ...

**World-building details**

- Timeframe
- Genre & atmosphere
- Important places

**Summary of the story**
"""
