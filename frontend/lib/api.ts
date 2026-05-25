export async function sendMessage(
    message: string,
    threadId: string
  ) {
    
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/chat`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          user_id: threadId,
        }),
      }
    );
  
    if (!response.ok) {
      throw new Error("Failed to send message");
    }
  
    return response.json();
  }