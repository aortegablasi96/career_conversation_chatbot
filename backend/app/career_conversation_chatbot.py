try:
    # Local only: trust the OS certificate store (e.g. antivirus HTTPS scanning on Windows).
    # Not in requirements.txt, so this is a no-op on Render.
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import asyncio
from agents import trace, gen_trace_id, Runner
from dotenv import load_dotenv

from graph.graph import Graph

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

    async def stream(self, message, history):
        """ Handle user message submission, yielding token and done events. """
        async for event in self.graph.astream_superstep(message, history):
            yield event

async def main(trace_id):
    import gradio as gr
    app = ChatbotService(trace_id)
    await app.setup()
    gr.ChatInterface(app.chat).launch(inbrowser=True)


if __name__ == "__main__":

    trace_id = gen_trace_id()
    with trace("Enhanced Research trace", trace_id=trace_id):
        print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
        asyncio.run(main(trace_id))
        