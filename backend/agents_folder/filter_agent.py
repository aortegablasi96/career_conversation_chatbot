from typing import Literal, Optional
from agents import Agent, ModelSettings
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4.1-nano"

INSTRUCTIONS = """
You are an intent classifier for a Career Chatbot representing Andreu Ortega.
Classify the latest user message. When in doubt, assume VALID.

--------------------------------------------------
SUBJECT RULE
--------------------------------------------------

The only valid subject is Andreu Ortega. Default to him for any career-related
or CV-style question that does not explicitly name someone else as the topic.

CRITICAL: Certification names, course names, and technical terms are NOT external
entities — they are topics within Andreu's career. Asking about them by name is
always about Andreu's background.

VALID — subject is Andreu (directly or implied):
- "Who are you?" / "What do you do?" / "Tell me about your experience"
- "Tell me about the CPMAI" / "What is the CPMAI certification?"  ← Andreu's cert
- "Tell me about the AI Engineer Agentic Track"  ← Andreu's course
- "Can you give me more details about what you did at ABB?"  ← company as context
- "tell me more" / "and that certification?" ← follow-ups inherit prior subject

INVALID — a person or organization IS the subject (not Andreu's career):
- "What certifications does Elon Musk have?"
- "What is ABB known for as a company?" / "Who founded Google?"

--------------------------------------------------
INTENT
--------------------------------------------------

"info"    → questions about Andreu's identity, background, education, skills,
            experience, projects, certifications, courses, achievements, hobbies
"contact" → user wants to be contacted, asks how to connect, or shares contact info

--------------------------------------------------
FOLLOW-UP
--------------------------------------------------

Mark is_followup = true if the message depends on prior context. This includes:
- pronouns or implicit references ("tell me more", "and that one?")
- asking about a specific item from a set previously listed in the conversation
  (e.g., the chatbot listed two courses and the user now asks about one of them)

Follow-ups are always VALID.
"""

class FilterOutput(BaseModel):
    """
    Structured output returned by the conversational filter agent.

    The filter validates whether the latest user message:
    1. Is related to Andreu Ortega.
    2. Belongs to an allowed conversational category.
    """

    valid: bool = Field(
        description=(
            "Whether the latest user message is considered valid for the Andreu Ortega assistant. "
            "A query is valid only if both the topic and the conversational subject are allowed."
        )
    )

    subject_is_andreu: bool = Field(
        description=(
            "Whether the conversational subject of the latest message is Andreu Ortega, either explicitly or implicitly through conversation continuity. "
            "Certification names (e.g. CPMAI, PMP), course names, and technologies are career topics — they do NOT make this False. "
            "Set to False only when the user explicitly asks about another person (e.g. Elon Musk) or an external organization as its own subject."
        )
    )

    classification: Optional[Literal["info", "contact"]] = Field(
        default=None,
        description=(
            "High-level intent classification of the user message. "
            "'info' means the user is asking about Andreu Ortega's background, skills, education, projects, certifications, experience, hobbies, or contact details. "
            "'contact' means the user wants to establish communication, be contacted, or shares contact information. "
            "Must be null when valid=False."
        )
    )

    detected_language: str = Field(
        default=None,
        description=(
            "ISO language code representing the language of the latest user message only. "
            "Examples: 'en', 'es', 'it', 'fr'. "
            "Conversation history must not influence language detection."
        )
    )

    is_followup: bool = Field(
        default=False,
        description=(
            "Whether the latest user message depends on previous conversation context to be correctly understood. "
            "Examples include pronouns, implicit references, or short continuations such as 'tell me more', 'where did you study that?', or 'how long did it take?'."
        )
    )

    detected_topic: Optional[
        Literal[
            "greeting",
            "education",
            "certifications",
            "skills",
            "projects",
            "career",
            "contact_request",
            "personal_background",
        ]
    ] = Field(
        default=None,
        description=(
            "Normalized conversational topic detected in the latest user message. "
            "This value is used to maintain structured conversational state and support follow-up queries."
        )
    )

    detected_entity: Optional[str] = Field(
        default=None,
        description=(
            "Specific entity currently being discussed in the conversation. "
            "Usually represents a certification, technology, framework, company, project, university, or similar concept related to Andreu Ortega. "
            "Examples: 'CPMAI', 'LangChain', 'CrewAI'."
        )
    )

    confidence: float = Field(
        description=(
            "Confidence score between 0.0 and 1.0 representing how confident the filter agent is about its classification decision."
        ),
        ge=0.0,
        le=1.0,
    )

filter_agent = Agent(
    name="FilterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    output_type=FilterOutput,
    model_settings=ModelSettings(temperature=0, max_tokens=500, prompt_cache_retention="in_memory"),
)
