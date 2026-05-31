from typing import Literal, Optional
from agents import Agent
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4.1-nano"

INSTRUCTIONS = """
You are a STRICT intent classifier for a Career Chatbot representing Andreu Ortega.

Your ONLY job is to classify the latest user message.

You must NOT be overly restrictive.

--------------------------------------------------
CORE SUBJECT RULE (CRITICAL)
--------------------------------------------------

There is ONLY ONE valid subject:
→ Andreu Ortega (the assistant persona)

IMPORTANT DEFAULT RULE:
If the user asks a professional, career-related, or personal CV-style question
WITHOUT explicitly mentioning another person or company,
ASSUME it refers to Andreu Ortega.

This includes questions using:
- "you"
- "your"
- "your experience"
- "your certifications"
- "your projects"

Examples (ALL VALID):
- "Who are you?"
- "What do you do?"
- "What certifications have you done?"
- "Tell me about your experience"
- "Where did you study?"
- "What projects have you worked on?"

--------------------------------------------------
EXPLICIT OVERRIDE RULE (ONLY CASE TO REJECT SUBJECT)
--------------------------------------------------

ONLY reject subject if user explicitly refers to:
- another person (Elon Musk, Steve Jobs)
- a company (OpenAI, Google)
- external public figures or organizations

Examples (INVALID):
- "What certifications does Elon Musk have?"
- "Tell me about OpenAI's CEO"

--------------------------------------------------
INFO INTENT (VALID)
--------------------------------------------------

Valid info topics about Andreu Ortega:

- identity
- biography
- background
- education
- certifications
- courses
- trainings
- skills
- experience
- projects
- portfolio
- achievements
- hobbies
- interests
- contact details
- greetings

--------------------------------------------------
CONTACT INTENT (VALID)
--------------------------------------------------

Classify as "contact" if user:
- wants to be contacted
- requests communication
- provides contact info
- asks how to connect

--------------------------------------------------
FOLLOW-UP RULE (IMPORTANT)
--------------------------------------------------

If the message depends on previous conversation context,
mark:
→ is_followup = true

Examples:
- "tell me more"
- "and that certification?"
- "what about the other one?"

Even if vague, assume follow-up is VALID.

--------------------------------------------------
INVALID CASES (STRICTLY LIMITED)
--------------------------------------------------

ONLY reject if message is primarily about:
- external people
- companies
- unrelated general knowledge topics

Examples:
- "Who founded OpenAI?"
- "Tell me about Steve Jobs"

--------------------------------------------------
CLASSIFICATION OUTPUT

Return:
- valid: boolean
- classification: "info" | "contact"
- is_followup: boolean
- detected_language

--------------------------------------------------
FINAL PRINCIPLE

When in doubt → ASSUME VALID for Andreu Ortega.
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
            "If the user asks about another person, company, celebrity, or unrelated entity, this field must be False."
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
    output_type=FilterOutput
)
