export class WarmingUpError extends Error {}
export class RateLimitError extends Error {}

export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "done"; content: string }
  | { type: "error" };

// Streams one chat turn from /chat/stream (server-sent events over a POST),
// calling onEvent for every `data: {json}` frame.
export async function streamMessage(
  message: string,
  threadId: string,
  onEvent: (event: StreamEvent) => void,
) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: threadId }),
  });

  if (response.status === 503) throw new WarmingUpError("warming_up");
  if (response.status === 429) throw new RateLimitError("rate_limited");
  if (!response.ok || !response.body) throw new Error("Failed to send message");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += value;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      if (frame.startsWith("data: ")) onEvent(JSON.parse(frame.slice(6)));
    }
  }
}
