export class WarmingUpError extends Error {}
export class RateLimitError extends Error {}

export async function sendMessage(message: string, threadId: string) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: threadId }),
  });

  if (response.status === 503) throw new WarmingUpError("warming_up");
  if (response.status === 429) throw new RateLimitError("rate_limited");
  if (!response.ok) throw new Error("Failed to send message");

  return response.json();
}
