import ChatWindow from "@/components/ChatWindow";
import ChatErrorBoundary from "@/components/ChatErrorBoundary";

export default function Home() {
  return (
    <ChatErrorBoundary>
      <ChatWindow />
    </ChatErrorBoundary>
  );
}