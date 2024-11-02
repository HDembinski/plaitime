from datetime import datetime
import numpy as np
from pai.data_models import Fact
import ollama
import logging

logger = logging.getLogger(__name__)


class RoleplayMemory:
    def __init__(self, facts, model="llama3.2"):
        """
        Initialize the narrative memory system
        """
        self.facts = facts
        self.model = model

        # Prompt template for narrative fact extraction
        self.fact_extraction_prompt = """
        Analyze the following roleplay excerpt and extract key story information.

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
                    "kind": "character_trait|relationship|event|backstory|world_building",
                    "content": "extracted fact",
                    "characters": {"list", "of", "involved", "characters"}
                }
            ]
        }
        
        Roleplay excerpt:
        {message}
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

    def extract_facts(self, message: str, active_characters: list[str]) -> list[Fact]:
        """
        Extract facts from a roleplay message
        """
        prompt = self.fact_extraction_prompt.format(
            message=message, characters=", ".join(active_characters)
        )
        response = ollama.generate(model=self.model, prompt=prompt)
        logger.info("extract_facts", response)

        try:
            extracted = Fact.model_validate_json(response)
            facts = []

            for fact_data in extracted["facts"]:
                fact = Fact(
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

    def store_fact(self, fact: Fact):
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

    def get_character_facts(self, character_name: str) -> List[Fact]:
        """Get all facts involving a specific character"""
        self.cursor.execute(
            """
        SELECT * FROM narrative_facts
        WHERE json_extract(characters, '$') LIKE ?
        """,
            (f"%{character_name}%",),
        )

        return [
            Fact(
                content=row[1],
                fact_type=row[2],
                characters=set(json.loads(row[3])),
                source_message=row[4],
                timestamp=row[5],
                embedding=np.frombuffer(row[6]) if row[6] is not None else None,
            )
            for row in self.cursor.fetchall()
        ]

    def get_relationship_context(self, char1: str, char2: str) -> List[Fact]:
        """Get facts about the relationship between two characters"""
        char1_facts = self.get_character_facts(char1)
        return [fact for fact in char1_facts if char2 in fact.characters]

    def search_relevant_facts(
        self, situation: str, active_characters: List[str], top_k: int = 5
    ) -> List[Fact]:
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
    ) -> List[Fact]:
        """
        Process a new roleplay message - extract and store narrative facts
        """
        facts = self.extract_narrative_facts(message, active_characters)
        for fact in facts:
            self.store_fact(fact)
        return facts
