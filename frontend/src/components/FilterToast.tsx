import { FilterError } from "../types";

interface FilterToastProps {
  error: FilterError;
  onDismiss: () => void;
}

export default function FilterToast({ error, onDismiss }: FilterToastProps) {
  return (
    <div style={styles.toast}>
      <span style={styles.icon}>⚠️</span>
      <span style={styles.message}>{error.message}</span>
      <button onClick={onDismiss} style={styles.dismiss}>✕</button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toast: { display: "flex", alignItems: "center", gap: "10px", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: "8px", padding: "10px 16px", margin: "0 80px 12px", fontSize: "13px", color: "#856404", boxShadow: "0 2px 8px rgba(0,0,0,0.08)" },
  icon: { fontSize: "16px" },
  message: { flex: 1 },
  dismiss: { background: "none", border: "none", cursor: "pointer", fontSize: "14px", color: "#856404" },
};
