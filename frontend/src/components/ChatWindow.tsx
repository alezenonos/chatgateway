import { useEffect, useRef } from "react";
import { Message } from "../types";
import MessageBubble from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
}

export default function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.welcomeTitle}>Smith<span style={{ color: "#c8102e" }}>+</span>Howard Chat</div>
        <p style={styles.welcomeSub}>Your secure AI assistant for tax, accounting & advisory work</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { flex: 1, overflowY: "auto", padding: "28px 80px", display: "flex", flexDirection: "column", gap: "24px", background: "#f5f5f5" },
  empty: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#f5f5f5" },
  welcomeTitle: { fontSize: "28px", fontWeight: 700, color: "#1a1a1a", fontFamily: "Georgia, serif" },
  welcomeSub: { fontSize: "13px", color: "#777", marginTop: "4px" },
};
