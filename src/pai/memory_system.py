from typing import List, Optional, Set
import json
from dataclasses import dataclass
from datetime import datetime
import sqlite3
import numpy as np
from pai import CHARACTER_DIRECTORY


@dataclass
class NarrativeFact:
    content: str
    fact_type: (
        str  # 'character_trait', 'relationship', 'event', 'backstory', 'world_building'
    )
    characters: Set[str]  # Characters involved in this fact
    source_message: str
    timestamp: str
    embedding: Optional[np.ndarray] = None


class RoleplayMemory:
    def __init__(self, uid, llm):
        """
        Initialize the narrative memory system

        Args:
            llm: The LLM to use for narrative fact extraction and creating embeddings.
        """
        self.uid = uid
        self.llm = llm
        self.setup_database()

        # Prompt template for narrative fact extraction
        self.fact_extraction_prompt = """
        Analyze the following roleplay message and extract key story information.
        Focus on:
        1. Character traits and descriptions
        2. Relationships between characters
        3. Important events or actions
        4. Character backstory elements
        5. World-building details
        
        Return the response in JSON format with the following structure:
        {
            "facts": [
                {
                    "content": "extracted fact",
                    "fact_type": "character_trait|relationship|event|backstory|world_building",
                    "characters": ["list", "of", "character", "names"]
                }
            ]
        }
        
        Message: {message}
        Current characters in scene: {characters}
        """

        self.character_context_prompt = """
        Given these previous facts about characters and their relationships,
        summarize the most relevant information for the current situation.
        Focus on:
        1. Direct relationships between involved characters
        2. Relevant backstory elements
        3. Recent important events
        4. Character traits that might affect the current scene
        
        Facts:
        {facts}
        
        Current characters in scene: {characters}
        Current situation: {situation}
        """

    def setup_database(self):
        """Initialize SQLite database for storing narrative facts"""
        self.conn = sqlite3.connect(CHARACTER_DIRECTORY / f"{self.uid}.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS narrative_facts (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            characters TEXT NOT NULL,
            source_message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            embedding BLOB
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            name TEXT PRIMARY KEY,
            first_appearance TEXT NOT NULL
        )
        """)
        self.conn.commit()

    def extract_narrative_facts(
        self, message: str, active_characters: List[str]
    ) -> List[NarrativeFact]:
        """
        Extract narrative facts from a roleplay message
        """
        prompt = self.fact_extraction_prompt.format(
            message=message, characters=", ".join(active_characters)
        )
        response = self.llm(prompt)

        try:
            extracted = json.loads(response)
            facts = []

            for fact_data in extracted["facts"]:
                fact = NarrativeFact(
                    content=fact_data["content"],
                    fact_type=fact_data["fact_type"],
                    characters=set(fact_data["characters"]),
                    source_message=message,
                    timestamp=datetime.now().isoformat(),
                )
                # Generate embedding for the fact
                fact.embedding = self.encoder.encode(fact.content)
                facts.append(fact)

            return facts
        except (json.JSONDecodeError, KeyError):
            print("Error parsing LLM response")
            return []

    def store_fact(self, fact: NarrativeFact):
        """Store a narrative fact in the database"""
        self.cursor.execute(
            """
        INSERT INTO narrative_facts 
        (content, fact_type, characters, source_message, timestamp, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                fact.content,
                fact.fact_type,
                json.dumps(list(fact.characters)),
                fact.source_message,
                fact.timestamp,
                fact.embedding.tobytes() if fact.embedding is not None else None,
            ),
        )

        # Update character records
        for character in fact.characters:
            self.cursor.execute(
                """
            INSERT OR IGNORE INTO characters (name, first_appearance)
            VALUES (?, ?)
            """,
                (character, fact.timestamp),
            )

        self.conn.commit()

    def get_character_facts(self, character_name: str) -> List[NarrativeFact]:
        """Get all facts involving a specific character"""
        self.cursor.execute(
            """
        SELECT * FROM narrative_facts
        WHERE json_extract(characters, '$') LIKE ?
        """,
            (f"%{character_name}%",),
        )

        return [
            NarrativeFact(
                content=row[1],
                fact_type=row[2],
                characters=set(json.loads(row[3])),
                source_message=row[4],
                timestamp=row[5],
                embedding=np.frombuffer(row[6]) if row[6] is not None else None,
            )
            for row in self.cursor.fetchall()
        ]

    def get_relationship_context(self, char1: str, char2: str) -> List[NarrativeFact]:
        """Get facts about the relationship between two characters"""
        char1_facts = self.get_character_facts(char1)
        return [fact for fact in char1_facts if char2 in fact.characters]

    def search_relevant_facts(
        self, situation: str, active_characters: List[str], top_k: int = 5
    ) -> List[NarrativeFact]:
        """
        Search for relevant narrative facts based on the current situation
        and active characters
        """
        query_embedding = self.encoder.encode(situation)

        # Get facts involving any of the active characters
        character_facts = []
        for character in active_characters:
            character_facts.extend(self.get_character_facts(character))

        # Calculate similarities and sort
        similarities = []
        for fact in character_facts:
            if fact.embedding is not None:
                similarity = np.dot(query_embedding, fact.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(fact.embedding)
                )
                similarities.append((similarity, fact))

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in similarities[:top_k]]

    def get_scene_context(self, situation: str, active_characters: List[str]) -> str:
        """
        Get relevant context for the current scene
        """
        relevant_facts = self.search_relevant_facts(situation, active_characters)

        # Use the LLM to summarize relevant information
        summary_prompt = self.character_context_prompt.format(
            facts="\n".join([f"• {fact.content}" for fact in relevant_facts]),
            characters=", ".join(active_characters),
            situation=situation,
        )

        return self.llm(summary_prompt)

    def process_roleplay_message(
        self, message: str, active_characters: List[str]
    ) -> List[NarrativeFact]:
        """
        Process a new roleplay message - extract and store narrative facts
        """
        facts = self.extract_narrative_facts(message, active_characters)
        for fact in facts:
            self.store_fact(fact)
        return facts
