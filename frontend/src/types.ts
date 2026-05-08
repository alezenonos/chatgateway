export interface Message {
  role: "user" | "assistant";
  content: string;
  fileName?: string;
  fileContent?: string;
}

export interface FilterError {
  error: "content_filtered";
  message: string;
  rule: string;
}

export interface User {
  email: string;
  name: string;
}
