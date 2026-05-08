import { useState, useRef } from "react";

interface InputBarProps {
  onSend: (content: string, file?: File) => void;
  disabled: boolean;
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() && !file) return;
    onSend(text.trim(), file || undefined);
    setText("");
    setFile(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div style={styles.container}>
      {file && (
        <div style={styles.filePreview}>
          📄 {file.name}
          <button onClick={() => setFile(null)} style={styles.removeFile}>✕</button>
        </div>
      )}
      <form onSubmit={handleSubmit} style={styles.form}>
        <button type="button" onClick={() => fileRef.current?.click()} style={styles.attach} title="Attach file">📎</button>
        <input ref={fileRef} type="file" hidden accept=".csv,.xlsx,.pdf,.txt,.png,.jpg" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <textarea value={text} onChange={(e) => setText(e.target.value)} onKeyDown={handleKeyDown} placeholder="Message Smith+Howard Chat..." style={styles.input} rows={1} disabled={disabled} />
        <button type="submit" disabled={disabled || (!text.trim() && !file)} style={styles.send}>Send</button>
      </form>
      <p style={styles.notice}>Messages are scanned for sensitive data before being sent. Conversations are not stored on the server.</p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: "16px 80px 22px", background: "#f5f5f5", borderTop: "1px solid #e8e8e8" },
  filePreview: { display: "inline-flex", alignItems: "center", gap: "8px", background: "#e8e8e8", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", marginBottom: "8px" },
  removeFile: { background: "none", border: "none", cursor: "pointer", fontSize: "12px", color: "#666" },
  form: { display: "flex", alignItems: "flex-end", gap: "8px", background: "#ffffff", border: "1px solid #d0d0d0", borderRadius: "16px", padding: "12px 16px", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" },
  attach: { background: "none", border: "none", fontSize: "18px", cursor: "pointer", padding: "2px" },
  input: { flex: 1, border: "none", outline: "none", fontSize: "14px", resize: "none", fontFamily: "inherit", lineHeight: 1.4 },
  send: { background: "#1a1a1a", border: "none", color: "white", borderRadius: "8px", padding: "7px 16px", fontSize: "13px", cursor: "pointer", fontWeight: 500 },
  notice: { textAlign: "center", marginTop: "8px", fontSize: "11px", color: "#aaa" },
};
