import asyncio
from agents import trace, gen_trace_id, Runner
import gradio as gr
from dotenv import load_dotenv

from graph import Graph

load_dotenv(override=True)

class ChatbotService:
    def __init__(self, trace_id: str):
        self.graph = Graph(trace_id)
        self.initialized = False

    async def setup(self):
        if not self.initialized:
            await self.graph.setup()
            self.initialized = True
          
    async def chat(self, message, history):   
        """ Handle user message submission. """
        results = await self.graph.run_superstep(
                message, history
            )

        return results
    
async def main(trace_id):
    app = ChatbotService(trace_id)
    await app.setup()
    gr.ChatInterface(app.chat).launch(inbrowser=True)


if __name__ == "__main__":

    trace_id = gen_trace_id()
    with trace("Enhanced Research trace", trace_id=trace_id):
        print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
        asyncio.run(main(trace_id))
        