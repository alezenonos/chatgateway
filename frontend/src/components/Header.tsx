import { useState, useEffect } from "react";

interface HeaderProps {
  username: string | null;
  onNewChat: () => void;
  onLogout: () => void;
}

function getInitials(username: string): string {
  const parts = username.split(".");
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return username.slice(0, 2).toUpperCase();
}

export default function Header({ username, onNewChat, onLogout }: HeaderProps) {
  const [modelName, setModelName] = useState("Loading...");

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((data) => setModelName(data.model))
      .catch(() => setModelName("Unknown"));
  }, []);

  return (
    <header style={styles.header}>
      <div style={styles.brand}>
        <span style={styles.brandName}>Smith</span>
        <span style={styles.plus}>+</span>
        <span style={styles.brandName}>Howard</span>
        <span style={styles.divider} />
        <span style={styles.label}>CHAT</span>
      </div>
      <div style={styles.right}>
        <span style={styles.model}>{modelName}</span>
        <button onClick={onNewChat} style={styles.newChat}>+ New Chat</button>
        {username && (
          <button onClick={onLogout} style={styles.avatar} title={username}>
            {getInitials(username)}
          </button>
        )}
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 24px", background: "#1a1a1a", borderBottom: "2px solid #c8102e" },
  brand: { display: "flex", alignItems: "center", gap: "4px" },
  brandName: { fontSize: "22px", fontWeight: 700, color: "#ffffff", fontFamily: "Georgia, serif" },
  plus: { fontSize: "22px", fontWeight: 700, color: "#c8102e", fontFamily: "Georgia, serif" },
  divider: { width: "1px", height: "24px", background: "#444", margin: "0 12px" },
  label: { fontSize: "14px", fontWeight: 500, color: "#aaa", letterSpacing: "0.5px" },
  right: { display: "flex", alignItems: "center", gap: "16px" },
  model: { fontSize: "11px", color: "#999", background: "#2a2a2a", padding: "4px 12px", borderRadius: "12px" },
  newChat: { background: "none", border: "1px solid #444", color: "#ccc", borderRadius: "6px", padding: "5px 12px", fontSize: "12px", cursor: "pointer" },
  avatar: { width: "30px", height: "30px", borderRadius: "50%", background: "#2a4a7f", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", color: "white", fontWeight: 600, border: "none", cursor: "pointer" },
};
