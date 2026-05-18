from typing import Literal, Optional
from agents import Agent
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are a filter agent representing Andreu Ortega.

Your job is to decide whether the user's message is asking about Andreu Ortega (you).
The user does NOT need to mention "Andreu" explicitly.

There are two types of valid messages:

    "Info" messages:

        Treat the "Info" message as being about Andreu Ortega if it asks about:
        - identity (e.g. "who are you?", "tell me about yourself")
        - soft skills, strengths and weaknesses
        - education (e.g. "what school did you go to?", "what did you study?")
        - work experience, skills, career
        - projects, portfolio, achievements
        - personal life, hobbies, interests
        - background, biography, origin, location
        - your contact details (e.g. "which are your contact details", "can share your contact details", "can you give to me your contact details")

        The user can also salute you (e.g. "hello", "hi", "good morning", "good afternoon", "good evening", "good night").

    "Contact" messages:
        Treat the "Contact" message as:
        - The user wants to be contacted (e.g. "I would like to be contacted", "I want to be contacted", "How can we get in touch?").
        - The user provides his contact details (name, email) or the reason on why he wants to be contacted.

If the user is asking to be contacted, it should be classified as "contact". If the user is asking about your contact details, then should be classified as "info".
If the user is salutating in the same message that is asking to be contacted, classify it as contact.

Output Rules:
    - If it's any of the described types, the response should be TRUE as it is a valid message.
    - If the message isn't any of the described types, then the response should be FALSE as the message is not valid.
    - If the message is not valid, 'message_type' MUST be null.
    - Finally, write a message to the user about the filtering result. If invalid, ask the user to ask something again, this time related with your profesional life.
"""


class FilteredResponse(BaseModel):
    valid_response: bool = Field(description="A boolean value indicating if the query is related with Andreu or not")
    message_type: Optional[Literal["info","contact"]] = Field(description="Indicates if the message's purpose is to ask for information or to get contacted")
    message_for_user: str = Field(description="Message for the user indicating if query is valid or not, which would require to ask something again")

filter_agent = Agent(
    name="FilterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    output_type=FilteredResponse    
)

        