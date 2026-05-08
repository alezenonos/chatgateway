import { useState, useEffect } from "react";
import { fetchUsers } from "../services/api";

interface LoginPageProps {
  onLogin: (username: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [users, setUsers] = useState<string[]>([]);
  const [selected, setSelected] = useState("");

  useEffect(() => {
    fetchUsers().then(setUsers);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) onLogin(selected);
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <span style={styles.brandName}>Smith</span>
          <span style={styles.plus}>+</span>
          <span style={styles.brandName}>Howard</span>
        </div>
        <p style={styles.subtitle}>Chat — Development Login</p>
        <form onSubmit={handleSubmit} style={styles.form}>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={styles.select}>
            <option value="">Select a user...</option>
            {users.map((u) => (<option key={u} value={u}>{u}</option>))}
          </select>
          <button type="submit" disabled={!selected} style={styles.button}>Sign In</button>
        </form>
        <p style={styles.note}>This is a development login. In production, this will redirect to your corporate SSO.</p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "#f5f5f5" },
  card: { background: "#fff", borderRadius: "12px", padding: "48px", boxShadow: "0 2px 12px rgba(0,0,0,0.08)", textAlign: "center", maxWidth: "400px", width: "100%" },
  brand: { display: "flex", alignItems: "center", justifyContent: "center", gap: "4px", marginBottom: "8px" },
  brandName: { fontSize: "28px", fontWeight: 700, color: "#1a1a1a", fontFamily: "Georgia, serif" },
  plus: { fontSize: "28px", fontWeight: 700, color: "#c8102e", fontFamily: "Georgia, serif" },
  subtitle: { color: "#666", fontSize: "14px", marginBottom: "32px" },
  form: { display: "flex", flexDirection: "column", gap: "12px" },
  select: { padding: "12px", borderRadius: "8px", border: "1px solid #ddd", fontSize: "14px" },
  button: { padding: "12px", borderRadius: "8px", border: "none", background: "#1a1a1a", color: "#fff", fontSize: "14px", fontWeight: 600, cursor: "pointer" },
  note: { marginTop: "24px", fontSize: "11px", color: "#999" },
};
