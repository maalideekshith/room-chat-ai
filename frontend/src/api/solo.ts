import { authenticatedRequest } from "./auth"

export type Provider = "openai" | "anthropic" | "gemini"

export interface ProviderInfo {
  id: Provider
}

export interface Conversation {
  id: string
  title: string
  provider: Provider | null
  credential_id: string | null
  model: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: "user" | "assistant"
  content: string
  source_refs: string[]
  created_at: string
}

export interface Credential {
  id: string
  provider: Provider
  label: string
  key_suffix: string
  status: "active" | "invalid" | "revoked"
  last_validated_at: string | null
  created_at: string
}

export interface KnowledgeSource {
  id: string
  kind: "file" | "url"
  title: string
  url: string | null
  mime_type: string | null
  size_bytes: number | null
  status: "processing" | "ready" | "failed"
  error_code: string | null
  created_at: string
  processed_at: string | null
}

export interface Preferences {
  provider: Provider | null
  credential_id: string | null
  model: string | null
}

const root = "/api/v1/solo"

export const soloApi = {
  providers: () => authenticatedRequest<{ providers: ProviderInfo[] }>(`${root}/providers`),
  conversations: () => authenticatedRequest<Conversation[]>(`${root}/conversations`),
  conversation: (id: string) => authenticatedRequest<Conversation>(`${root}/conversations/${id}`),
  createConversation: (title = "New conversation") => authenticatedRequest<Conversation>(`${root}/conversations`, {
    method: "POST", body: JSON.stringify({ title }),
  }),
  renameConversation: (id: string, title: string) => authenticatedRequest<Conversation>(`${root}/conversations/${id}`, {
    method: "PATCH", body: JSON.stringify({ title }),
  }),
  deleteConversation: (id: string) => authenticatedRequest<void>(`${root}/conversations/${id}`, { method: "DELETE" }),
  messages: (id: string) => authenticatedRequest<Message[]>(`${root}/conversations/${id}/messages`),
  sendMessage: (id: string, content: string) => authenticatedRequest<Message[]>(`${root}/conversations/${id}/messages`, {
    method: "POST", body: JSON.stringify({ content }),
  }),
  conversationSettings: (id: string, settings: Preferences) => authenticatedRequest<Conversation>(
    `${root}/conversations/${id}/ai-settings`, { method: "PUT", body: JSON.stringify(settings) },
  ),
  credentials: () => authenticatedRequest<Credential[]>(`${root}/credentials`),
  credentialModels: (id: string) => authenticatedRequest<{ models: string[] }>(`${root}/credentials/${id}/models`),
  addCredential: (provider: Provider, label: string, api_key: string) => authenticatedRequest<Credential>(
    `${root}/credentials`, { method: "POST", body: JSON.stringify({ provider, label, api_key }) },
  ),
  updateCredential: (id: string, label: string, api_key?: string) => authenticatedRequest<Credential>(
    `${root}/credentials/${id}`, {
      method: "PATCH", body: JSON.stringify({ label, ...(api_key ? { api_key } : {}) }),
    },
  ),
  deleteCredential: (id: string) => authenticatedRequest<void>(`${root}/credentials/${id}`, { method: "DELETE" }),
  preferences: () => authenticatedRequest<Preferences>(`${root}/preferences`),
  updatePreferences: (settings: Preferences) => authenticatedRequest<Preferences>(`${root}/preferences`, {
    method: "PUT", body: JSON.stringify(settings),
  }),
  sources: () => authenticatedRequest<KnowledgeSource[]>(`${root}/sources`),
  uploadSource: (file: File) => {
    const body = new FormData()
    body.set("file", file)
    return authenticatedRequest<KnowledgeSource>(`${root}/sources/files`, { method: "POST", body })
  },
  addUrl: (url: string) => authenticatedRequest<KnowledgeSource>(`${root}/sources/urls`, {
    method: "POST", body: JSON.stringify({ url }),
  }),
  deleteSource: (id: string) => authenticatedRequest<void>(`${root}/sources/${id}`, { method: "DELETE" }),
}
