import { useState, useCallback, useRef } from "react";
import { Message, FilterError } from "../types";
import { streamChat, uploadFile } from "../services/api";

const STORAGE_KEY = "sh_messages";

function loadMessages(): Message[] {
  const stored = sessionStorage.getItem(STORAGE_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

function saveMessages(messages: Message[]) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
}

export function useChat(token: string | null) {
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [isStreaming, setIsStreaming] = useState(false);
  const [filterError, setFilterError] = useState<FilterError | null>(null);
  const abortRef = useRef(false);

  const clearChat = useCallback(() => {
    setMessages([]);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  const dismissFilter = useCallback(() => {
    setFilterError(null);
  }, []);

  const sendMessage = useCallback(
    async (content: string, file?: File) => {
      if (!token) return;

      let fileContent: string | undefined;
      let fileName: string | undefined;

      if (file) {
        const uploadResult = await uploadFile(file, token);
        if ("error" in uploadResult) {
          setFilterError(uploadResult as FilterError);
          return;
        }
        fileContent = uploadResult.file_content;
        fileName = uploadResult.file_name;
      }

      const userMessage: Message = { role: "user", content, fileName, fileContent };
      const updated = [...messages, userMessage];
      setMessages(updated);
      saveMessages(updated);

      const assistantMessage: Message = { role: "assistant", content: "" };
      const withAssistant = [...updated, assistantMessage];
      setMessages(withAssistant);
      setIsStreaming(true);
      abortRef.current = false;

      let accumulated = "";

      const apiMessages = updated.map((m) => ({
        role: m.role,
        content: m.content,
        file_content: m.fileContent || null,
        file_name: m.fileName || null,
      }));

      await streamChat(
        apiMessages,
        token,
        (chunk) => {
          if (abortRef.current) return;
          accumulated += chunk;
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { role: "assistant", content: accumulated };
            return copy;
          });
        },
        () => {
          setIsStreaming(false);
          setMessages((prev) => {
            saveMessages(prev);
            return prev;
          });
        },
        (err) => {
          setIsStreaming(false);
          setFilterError(err);
          setMessages(updated);
          saveMessages(updated);
        }
      );
    },
    [token, messages]
  );

  return {
    messages,
    isStreaming,
    filterError,
    sendMessage,
    clearChat,
    dismissFilter,
  };
}
