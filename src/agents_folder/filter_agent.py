from typing import Literal, Optional
from agents import Agent
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are a filter agent representing Andreu Ortega.

Your job is to decide whether the user's message is asking about Andreu Ortega (you).
The user does NOT need to mention "Andreu" explicitly.

Treat the message as being about Andreu Ortega if it asks about:
- identity (e.g. "who are you?", "tell me about yourself")
- education (e.g. "what school did you go to?", "what did you study?")
- work experience, skills, career
- projects, portfolio, achievements
- personal life, hobbies, interests
- background, biography, origin, location

As an exception, the user can also salute you (e.g. "hello", "hi", "good morning", "good afternoon", "good evening", "good night")

As an exception, the user could also want to be contacted (e.g. "I want to be contacted", "How can we get in touch?") or provide his contact details. That also has to be a valid message.
'user_details' output MUST be null if the following 'user_details' fields (name, email) are null.

In case of being a valid message, you also need to identify if the user is asking about Andreu Ortega (which also would include saluting you) or is requesting to be contacted (in 'message_type'). 
If the message is not valid, 'message_type' MUST be null.
"""

class UserDetails(BaseModel):
    name: Optional[str] = Field(description="Name of the user")
    email: Optional[str] = Field(description="Email of the user")
    reason: Optional[str] = Field(description="Details which topic would like to be discussed")

class FilteredResponse(BaseModel):
    response: bool = Field(description="A boolean value indicating if the query is related with Andreu or not")
    user_details: Optional[UserDetails] = Field(description="User contact details")
    message_type: Optional[Literal["info","contact"]] = Field(description="Indicates if the message's purpose is to ask for information or to get contacted")

filter_agent = Agent(
    name="FilterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    output_type=FilteredResponse    
)

        