from agents import Agent
from pydantic import BaseModel,Field

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
"""

class FilteredResponse(BaseModel):
    response: bool = Field(description="A boolean value indicating if the query is related with Andreu or not")

filter_agent = Agent(
    name="FilterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    output_type=FilteredResponse    
)

        