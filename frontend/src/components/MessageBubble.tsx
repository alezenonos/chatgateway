import ReactMarkdown from "react-markdown";
import { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", gap: "10px" }}>
      {!isUser && <div style={styles.badge}>S+H</div>}
      <div style={isUser ? styles.userBubble : styles.assistantBubble}>
        {isUser ? (
          <>
            <p style={{ margin: 0 }}>{message.content}</p>
            {message.fileName && (
              <div style={styles.fileAttachment}>📄 {message.fileName}</div>
            )}
          </>
        ) : (
          <div style={styles.markdown}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {isStreaming && <span style={styles.cursor} />}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  badge: { minWidth: "28px", height: "28px", borderRadius: "6px", background: "#1a1a1a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "10px", color: "#c8102e", fontWeight: 700, marginTop: "2px" },
  userBubble: { background: "#1a1a1a", borderRadius: "16px 16px 4px 16px", padding: "14px 18px", maxWidth: "65%", fontSize: "14px", color: "#f0f0f0", lineHeight: 1.5 },
  assistantBubble: { background: "#ffffff", border: "1px solid #e0e0e0", borderRadius: "16px 16px 16px 4px", padding: "14px 18px", maxWidth: "70%", fontSize: "14px", color: "#333", lineHeight: 1.7, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  fileAttachment: { marginTop: "10px", padding: "8px 12px", background: "#2a2a2a", borderRadius: "8px", fontSize: "12px", color: "#aaa" },
  markdown: { overflow: "hidden" },
  cursor: { display: "inline-block", width: "8px", height: "16px", background: "#c8102e", borderRadius: "2px", verticalAlign: "middle", animation: "blink 1s infinite" },
};
