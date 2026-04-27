from agents import trace, gen_trace_id, Runner
import gradio as gr
from dotenv import load_dotenv

from agents_folder.router_agent import router_agent

load_dotenv(override=True)

          
async def chat(message, history):
    
    messages = []

    if history:
        for msg in history:
            messages.append({"role": msg["role"],"content": msg["content"][0]["text"]})

    messages.append({"role": "user", "content": message})
    
    result = await Runner.run(
            router_agent,
            messages,
        )
    return result.final_output


if __name__ == "__main__":

    trace_id = gen_trace_id()
    with trace("Enhanced Research trace", trace_id=trace_id):
        print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
        gr.ChatInterface(chat).launch(inbrowser=True)