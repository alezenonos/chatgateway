import { FilterError } from "../types";

const BASE = "/api";

function getHeaders(token: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchUsers(): Promise<string[]> {
  const res = await fetch(`${BASE}/auth/users`);
  const data = await res.json();
  return data.users;
}

export async function login(username: string): Promise<string> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.token;
}

export async function uploadFile(
  file: File,
  token: string
): Promise<{ file_name: string; file_content: string } | FilterError> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/files/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (res.status === 403) {
    const detail = await res.json();
    return detail.detail as FilterError;
  }
  if (res.status === 400) {
    const detail = await res.json();
    return detail.detail as FilterError;
  }
  if (!res.ok) throw new Error("Upload failed");
  return await res.json();
}

export async function streamChat(
  messages: { role: string; content: string; file_content?: string | null; file_name?: string | null }[],
  token: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: FilterError) => void
): Promise<void> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({ messages }),
  });

  if (res.status === 403) {
    const detail = await res.json();
    onError(detail.detail as FilterError);
    return;
  }

  if (!res.ok) throw new Error("Chat request failed");

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    const lines = text.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          onDone();
          return;
        }
        onChunk(data);
      }
    }
  }
  onDone();
}
