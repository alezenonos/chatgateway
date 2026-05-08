import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import Header from "./components/Header";
import LoginPage from "./components/LoginPage";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import FilterToast from "./components/FilterToast";

export default function App() {
  const { token, username, isAuthenticated, login, logout } = useAuth();
  const { messages, isStreaming, filterError, sendMessage, clearChat, dismissFilter } = useChat(token);

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header username={username} onNewChat={clearChat} onLogout={logout} />
      <ChatWindow messages={messages} isStreaming={isStreaming} />
      {filterError && <FilterToast error={filterError} onDismiss={dismissFilter} />}
      <InputBar onSend={sendMessage} disabled={isStreaming} />
      <style>{`@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }`}</style>
    </div>
  );
}
