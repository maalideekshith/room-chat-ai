import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { ApiError } from "../api/auth"
import {
  soloApi,
  type Conversation,
  type Credential,
  type KnowledgeSource,
  type Message,
  type Preferences,
  type Provider,
  type ProviderInfo,
} from "../api/solo"
import { useAuth } from "../auth/AuthContext"
import { BrandMark } from "../components/Brand"
import { Icon } from "../components/Icon"

type WorkspaceView = "chat" | "knowledge" | "providers"
interface RoomRouteState {
  conversationId?: string
  workspaceView?: WorkspaceView
}

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "We couldn’t complete that request. Please try again."
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    .format(new Date(value))
}

function ConversationRow({
  item, active, onSelect, onRename, onDelete,
}: {
  item: Conversation
  active: boolean
  onSelect(): void
  onRename(): void
  onDelete(): void
}) {
  const [menu, setMenu] = useState(false)
  return (
    <div className={`history-row${active ? " history-row--active" : ""}`}>
      <button className="history-row__open" type="button" onClick={onSelect} aria-current={active ? "page" : undefined}>
        <Icon name="messages" />
        <span><strong>{item.title}</strong><small>{dateLabel(item.updated_at)}</small></span>
      </button>
      <button className="history-row__menu" type="button" aria-label={`Conversation actions for ${item.title}`}
        aria-expanded={menu} onClick={() => setMenu((state) => !state)}>
        <Icon name="dots" />
      </button>
      {menu && <div className="history-row__popover">
        <button type="button" onClick={() => { setMenu(false); onRename() }}>Rename</button>
        <button type="button" className="text-danger" onClick={() => { setMenu(false); onDelete() }}>Delete</button>
      </div>}
    </div>
  )
}

export default function DashboardPage() {
  const { signOut, signOutAll } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const routeState = location.state as RoomRouteState | null
  const requestedConversationId = routeState?.conversationId
  const [view, setView] = useState<WorkspaceView>(routeState?.workspaceView ?? "chat")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [credentialModels, setCredentialModels] = useState<Record<string, string[]>>({})
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [preferences, setPreferences] = useState<Preferences>({ provider: null, credential_id: null, model: null })
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [query, setQuery] = useState("")
  const [draft, setDraft] = useState("")
  const [pageLoading, setPageLoading] = useState(true)
  const [loadedMessagesFor, setLoadedMessagesFor] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [busy, setBusy] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [providerDraft, setProviderDraft] = useState<Provider>("openai")
  const [credentialLabel, setCredentialLabel] = useState("")
  const [credentialKey, setCredentialKey] = useState("")
  const [credentialSaving, setCredentialSaving] = useState(false)
  const [editCredentialId, setEditCredentialId] = useState<string | null>(null)
  const [editLabel, setEditLabel] = useState("")
  const [editKey, setEditKey] = useState("")
  const [urlDraft, setUrlDraft] = useState("")
  const [sourceBusy, setSourceBusy] = useState(false)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState("")
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [settingsSaving, setSettingsSaving] = useState(false)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const activeConversation = conversations.find((item) => item.id === activeId) ?? null
  const messagesLoading = Boolean(activeId && loadedMessagesFor !== activeId)
  const selectedProvider = activeConversation?.provider ?? preferences.provider
  const selectedCredential = activeConversation?.credential_id ?? preferences.credential_id
  const selectedModel = activeConversation?.model ?? preferences.model
  const selectedModelKey = selectedProvider && selectedCredential && selectedModel
    ? `${selectedProvider}|${selectedCredential}|${selectedModel}`
    : ""

  const filteredConversations = useMemo(() => {
    const term = query.trim().toLocaleLowerCase()
    return term ? conversations.filter((item) => item.title.toLocaleLowerCase().includes(term)) : conversations
  }, [conversations, query])

  useEffect(() => {
    let mounted = true
    Promise.all([
      soloApi.conversations(), soloApi.credentials(), soloApi.providers(), soloApi.preferences(), soloApi.sources(),
    ]).then(async ([nextConversations, nextCredentials, providerResponse, nextPreferences, nextSources]) => {
      if (!mounted) return
      setConversations(nextConversations)
      setCredentials(nextCredentials)
      setProviders(providerResponse.providers)
      const modelResults = await Promise.all(nextCredentials.map(async (credential) => {
        try { return [credential.id, (await soloApi.credentialModels(credential.id)).models] as const }
        catch { return [credential.id, []] as const }
      }))
      if (!mounted) return
      setCredentialModels(Object.fromEntries(modelResults))
      setPreferences(nextPreferences)
      setSources(nextSources)
      setActiveId((current) => (requestedConversationId
        && nextConversations.some((item) => item.id === requestedConversationId)
        ? requestedConversationId
        : current)
        ?? nextConversations[0]?.id
        ?? null)
    }).catch((cause: unknown) => {
      if (mounted) setError(errorText(cause))
    }).finally(() => { if (mounted) setPageLoading(false) })
    return () => { mounted = false }
  }, [requestedConversationId])

  useEffect(() => {
    if (!activeId) return
    let mounted = true
    soloApi.messages(activeId).then((rows) => { if (mounted) setMessages(rows) })
      .catch((cause: unknown) => { if (mounted) setError(errorText(cause)) })
      .finally(() => { if (mounted) setLoadedMessagesFor(activeId) })
    return () => { mounted = false }
  }, [activeId])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, messagesLoading])

  async function createConversation() {
    setBusy(true)
    setError(null)
    try {
      const created = await soloApi.createConversation()
      setConversations((items) => [created, ...items])
      setActiveId(created.id)
      setView("chat")
      setMobileNavOpen(false)
      setMessages([])
      setNotice("Conversation created")
    } catch (cause) { setError(errorText(cause)) }
    finally { setBusy(false) }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const content = draft.trim()
    if (!activeId || !content || sending) return
    setSending(true)
    setError(null)
    setDraft("")
    try {
      const saved = await soloApi.sendMessage(activeId, content)
      setMessages((items) => [...items, ...saved])
      const refreshed = await soloApi.conversations()
      setConversations(refreshed)
    } catch (cause) {
      setError(errorText(cause))
      try { setMessages(await soloApi.messages(activeId)) } catch { /* Keep the visible draft and prior history. */ }
    } finally { setSending(false); composerRef.current?.focus() }
  }

  function handleComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  async function chooseConversationModel(value: string) {
    if (!activeId || !value) return
    const [provider, credential_id, model] = value.split("|") as [Provider, string, string]
    setSettingsSaving(true)
    setError(null)
    try {
      const updated = await soloApi.conversationSettings(activeId, { provider, credential_id, model })
      setConversations((items) => items.map((item) => item.id === updated.id ? updated : item))
      setNotice("Conversation model updated")
    } catch (cause) { setError(errorText(cause)) }
    finally { setSettingsSaving(false) }
  }

  async function addCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCredentialSaving(true)
    setError(null)
    try {
      const row = await soloApi.addCredential(providerDraft, credentialLabel.trim(), credentialKey)
      setCredentials((items) => [...items, row])
      try {
        const result = await soloApi.credentialModels(row.id)
        setCredentialModels((items) => ({ ...items, [row.id]: result.models }))
      } catch { /* The credential remains connected; report model discovery when the user opens it. */ }
      setCredentialLabel("")
      setCredentialKey("")
      setNotice(`${row.label} connected`)
    } catch (cause) { setError(errorText(cause)) }
    finally { setCredentialSaving(false) }
  }

  async function saveCredentialEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editCredentialId) return
    setCredentialSaving(true)
    try {
      const row = await soloApi.updateCredential(editCredentialId, editLabel.trim(), editKey || undefined)
      setCredentials((items) => items.map((item) => item.id === row.id ? row : item))
      setEditCredentialId(null)
      setEditKey("")
      setNotice("Provider credential updated")
    } catch (cause) { setError(errorText(cause)) }
    finally { setCredentialSaving(false) }
  }

  async function removeCredential(credential: Credential) {
    if (!window.confirm(`Remove ${credential.label}? Existing messages will remain available.`)) return
    try {
      await soloApi.deleteCredential(credential.id)
      setCredentials((items) => items.filter((item) => item.id !== credential.id))
      setConversations(await soloApi.conversations())
      if (preferences.credential_id === credential.id) {
        const cleared = { provider: null, credential_id: null, model: null }
        setPreferences(cleared)
      }
      setNotice("Provider credential removed")
    } catch (cause) { setError(errorText(cause)) }
  }

  async function setAsDefault(credential: Credential) {
    const model = credentialModels[credential.id]?.[0]
    if (!model) return
    try {
      const updated = await soloApi.updatePreferences({
        provider: credential.provider, credential_id: credential.id, model,
      })
      setPreferences(updated)
      setNotice("Default AI model updated")
    } catch (cause) { setError(errorText(cause)) }
  }

  async function addUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSourceBusy(true)
    setError(null)
    try {
      const created = await soloApi.addUrl(urlDraft.trim())
      setSources((items) => [created, ...items])
      setUrlDraft("")
      setNotice(created.status === "ready" ? "Source added and ready" : "Source added but could not be processed")
    } catch (cause) { setError(errorText(cause)) }
    finally { setSourceBusy(false) }
  }

  async function uploadFile(file: File | undefined) {
    if (!file) return
    setSourceBusy(true)
    setError(null)
    try {
      const created = await soloApi.uploadSource(file)
      setSources((items) => [created, ...items])
      setNotice(created.status === "ready" ? "File added and ready" : "File added but could not be processed")
    } catch (cause) { setError(errorText(cause)) }
    finally { setSourceBusy(false); if (fileRef.current) fileRef.current.value = "" }
  }

  async function removeSource(source: KnowledgeSource) {
    try {
      await soloApi.deleteSource(source.id)
      setSources((items) => items.filter((item) => item.id !== source.id))
      setNotice("Knowledge source removed")
    } catch (cause) { setError(errorText(cause)) }
  }

  async function renameConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!renameId || !renameDraft.trim()) return
    try {
      const updated = await soloApi.renameConversation(renameId, renameDraft.trim())
      setConversations((items) => items.map((item) => item.id === updated.id ? updated : item))
      setRenameId(null)
      setNotice("Conversation renamed")
    } catch (cause) { setError(errorText(cause)) }
  }

  async function confirmDeleteConversation() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await soloApi.deleteConversation(deleteTarget.id)
      const remaining = conversations.filter((item) => item.id !== deleteTarget.id)
      setConversations(remaining)
      if (activeId === deleteTarget.id) {
        setActiveId(remaining[0]?.id ?? null)
        setMessages([])
      }
      setDeleteTarget(null)
      setNotice("Conversation deleted")
    } catch (cause) { setError(errorText(cause)) }
    finally { setDeleting(false) }
  }

  async function leave(all: boolean) {
    setBusy(true)
    const confirmed = all ? await signOutAll() : await signOut()
    navigate("/login", { replace: true, state: { notice: confirmed ? "You’re signed out." : "You’re signed out on this device." } })
  }

  const navContents = (
    <>
      <div className="solo-brand"><BrandMark compact /></div>
      <button className="solo-new-button" type="button" onClick={() => void createConversation()} disabled={busy || pageLoading}>
        <Icon name="plus" /><span>New conversation</span>
      </button>
      <div className="solo-sidebar-label">WORKSPACE</div>
      <nav className="solo-nav" aria-label="Solo workspace">
        <button className={view === "chat" ? "is-current" : ""} type="button" onClick={() => setView("chat")}><Icon name="messages" /> Conversations</button>
        <button className={view === "knowledge" ? "is-current" : ""} type="button" onClick={() => setView("knowledge")}><Icon name="knowledge" /> Knowledge sources <span>{sources.length}</span></button>
        <button className={view === "providers" ? "is-current" : ""} type="button" onClick={() => setView("providers")}><Icon name="settings" /> AI providers</button>
      </nav>
      <div className="history-heading"><span>RECENT</span><span>{conversations.length}</span></div>
      <label className="conversation-search"><Icon name="search" /><input aria-label="Search conversations" placeholder="Search history" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className="conversation-list" aria-label="Conversation history">
        {pageLoading ? <p className="sidebar-hint">Loading history…</p>
          : filteredConversations.length ? filteredConversations.map((item) => renameId === item.id ? (
            <form key={item.id} className="rename-form" onSubmit={(event) => void renameConversation(event)}>
              <input autoFocus aria-label="Conversation title" value={renameDraft} onChange={(event) => setRenameDraft(event.target.value)} maxLength={160} />
              <button type="submit" aria-label="Save conversation title"><Icon name="check" /></button>
              <button type="button" aria-label="Cancel rename" onClick={() => setRenameId(null)}><Icon name="close" /></button>
            </form>
          ) : <ConversationRow key={item.id} item={item} active={item.id === activeId}
            onSelect={() => { setMessages([]); setActiveId(item.id); setView("chat"); setMobileNavOpen(false) }}
            onRename={() => { setRenameId(item.id); setRenameDraft(item.title) }}
            onDelete={() => setDeleteTarget(item)} />)
            : <p className="sidebar-hint">{query ? "No matching conversations" : "Your conversations will appear here."}</p>}
      </div>
      <div className="solo-sidebar-bottom">
        <div className="solo-secure"><span className="status-dot" /> Private workspace</div>
        <p><BrandMark compact /> <span>Personal AI workspace</span></p>
      </div>
    </>
  )

  return (
    <div className="solo-shell">
      <aside className="solo-sidebar solo-sidebar--desktop">{navContents}</aside>
      {mobileNavOpen && <div className="solo-mobile-layer">
        <button className="solo-mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />
        <aside className="solo-sidebar solo-sidebar--mobile">
          <button className="solo-close-nav" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><Icon name="close" /></button>
          {navContents}
        </aside>
      </div>}
      <div className="solo-main">
        <header className="solo-topbar">
          <button className="solo-icon-button solo-menu-trigger" type="button" aria-label="Open workspace navigation" onClick={() => setMobileNavOpen(true)}><Icon name="menu" /></button>
          <Link className="solo-back-overview" to="/app"><Icon name="home" />Back to Overview</Link>
          <div className="solo-breadcrumb"><span>Solo</span><Icon name="chevron" /><strong>{view === "chat" ? activeConversation?.title ?? "New conversation" : view === "knowledge" ? "Knowledge sources" : "AI providers"}</strong></div>
          <div className="solo-top-actions">
            {activeConversation && view === "chat" && <label className="model-picker"><Icon name="spark" /><span className="visually-hidden">Conversation model</span>
              <select value={selectedModelKey} onChange={(event) => void chooseConversationModel(event.target.value)} disabled={settingsSaving || credentials.length === 0}>
                {!selectedModelKey && <option value="">Choose a model</option>}
                {selectedModelKey && !credentials.some((credential) => credentialModels[credential.id]?.some((model) => `${credential.provider}|${credential.id}|${model}` === selectedModelKey)) && <option value={selectedModelKey}>Current model</option>}
                {credentials.filter((item) => item.status === "active").flatMap((credential) =>
                  credentialModels[credential.id]?.map((model) => {
                    const value = `${credential.provider}|${credential.id}|${model}`
                    return <option key={value} value={value}>{credential.provider} · {model} · {credential.label}</option>
                  }) ?? [],
                )}
              </select>
              <Icon name="chevron" />
            </label>}
            <div className="solo-account-wrap">
              <button className="solo-account-button" type="button" aria-expanded={menuOpen} aria-haspopup="menu" onClick={() => setMenuOpen((open) => !open)} disabled={busy}>
                <span className="solo-avatar"><Icon name="user" /></span><span>My account</span><Icon name="chevron" />
              </button>
              {menuOpen && <div className="solo-account-menu" role="menu">
                <p>Signed in to Room Chat AI</p>
                <button type="button" role="menuitem" onClick={() => void leave(false)}><Icon name="logout" /> Sign out</button>
                <button type="button" role="menuitem" onClick={() => void leave(true)}><Icon name="shield" /> Sign out all sessions</button>
              </div>}
            </div>
          </div>
        </header>

        {(error || notice) && <div className={`solo-feedback${error ? " solo-feedback--error" : ""}`} role={error ? "alert" : "status"}>
          <span>{error ?? notice}</span><button type="button" aria-label="Dismiss notification" onClick={() => { setError(null); setNotice(null) }}><Icon name="close" /></button>
        </div>}

        {pageLoading ? <div className="solo-loading" role="status"><span className="spinner" /> Preparing your workspace…</div>
          : view === "chat" ? <main className="solo-chat-area">
            {!activeConversation ? <section className="solo-empty-state">
              <div className="solo-empty-mark"><Icon name="messages" /></div>
              <p className="solo-eyebrow">YOUR PERSONAL WORKSPACE</p>
              <h1>Make room for<br /><span>good thinking.</span></h1>
              <p className="solo-empty-copy">Start a private conversation with AI. Connect your own provider key to choose a model, and add documents or links whenever you want answers grounded in your knowledge.</p>
              <div className="solo-empty-actions"><button className="solo-primary-button" type="button" onClick={() => credentials.length ? void createConversation() : setView("providers")}>
                {credentials.length ? <><Icon name="plus" /> Start a conversation</> : <><Icon name="settings" /> Connect an AI provider</>}
              </button><button className="solo-secondary-button" type="button" onClick={() => setView("knowledge")}><Icon name="knowledge" /> Add knowledge sources</button></div>
              {credentials.length > 0 && <button className="solo-text-button" type="button" onClick={() => void createConversation()}>Create your first conversation <Icon name="arrow" /></button>}
            </section> : <>
              <div className="solo-messages" aria-label="Conversation messages" aria-live="polite">
                {messagesLoading ? <div className="solo-loading"><span className="spinner" /> Loading conversation…</div>
                  : messages.length === 0 ? <div className="solo-conversation-empty"><div className="solo-empty-mark"><Icon name="spark" /></div><h1>What are you working on?</h1><p>Your messages are private to this workspace. Ask a question or share what you’d like to explore.</p></div>
                    : messages.map((message) => <article className={`solo-message solo-message--${message.role}`} key={message.id}>
                      <span className="solo-message-avatar">{message.role === "user" ? <Icon name="user" /> : <BrandMark compact />}</span>
                      <div className="solo-message-content"><div className="solo-message-meta"><strong>{message.role === "user" ? "You" : "Room Chat AI"}</strong><time dateTime={message.created_at}>{dateLabel(message.created_at)}</time></div>
                        <p>{message.content}</p>
                        {!!message.source_refs.length && <div className="solo-citations"><span>Sources</span>{message.source_refs.map((id) => <span className="solo-citation" key={id}>{sources.find((source) => source.id === id)?.title ?? "Knowledge source"}</span>)}</div>}
                      </div>
                    </article>)}
                {sending && <div className="solo-thinking" role="status"><span className="spinner" /> Thinking…</div>}
                <div ref={endRef} />
              </div>
              <div className="solo-composer-wrap">
                {!selectedModelKey && <div className="solo-composer-callout"><Icon name="lock" />{credentials.length === 0
                  ? <><span>Connect your own AI provider key before sending a message.</span><button type="button" onClick={() => setView("providers")}>Set up provider</button></>
                  : <span>Choose a provider and model above before sending a message.</span>}</div>}
                <form className="solo-composer" onSubmit={(event) => void sendMessage(event)}>
                  <textarea ref={composerRef} aria-label="Message Room Chat AI" placeholder="Ask a question or start with an idea…" value={draft} maxLength={20_000} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleComposerKey} disabled={sending || !selectedModelKey} rows={2} />
                  <div className="solo-composer-toolbar"><div><button type="button" className="solo-attach-button" onClick={() => setView("knowledge")}><Icon name="paperclip" /> Add knowledge</button><span>Enter to send · Shift + Enter for a new line</span></div>
                    <button className="solo-send-button" type="submit" disabled={!draft.trim() || sending || !selectedModelKey} aria-label="Send message">{sending ? <span className="spinner" /> : <Icon name="arrow" />}</button></div>
                </form><p className="solo-composer-disclaimer">AI responses can be inaccurate. Review important information.</p>
              </div>
            </>}</main>
          : view === "providers" ? <main className="solo-settings-page">
            <div className="solo-page-heading"><p className="solo-eyebrow">PERSONAL AI</p><h1>AI providers</h1><p>Connect your own provider accounts. Keys are encrypted before storage and never shown again.</p></div>
            <section className="solo-settings-card"><div className="solo-card-heading"><div><h2>Connect a provider</h2><p>Credentials are validated with the provider before they’re saved.</p></div><span className="solo-card-icon"><Icon name="lock" /></span></div>
              <form className="solo-provider-form" onSubmit={(event) => void addCredential(event)}>
                <label>Provider<select value={providerDraft} onChange={(event) => setProviderDraft(event.target.value as Provider)}>{providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.id === "gemini" ? "Google Gemini" : provider.id === "anthropic" ? "Anthropic Claude" : "OpenAI"}</option>)}</select></label>
                <label>Credential name<input value={credentialLabel} onChange={(event) => setCredentialLabel(event.target.value)} placeholder="Personal account" maxLength={80} required /></label>
                <label className="solo-key-field">API key<input type="password" value={credentialKey} onChange={(event) => setCredentialKey(event.target.value)} autoComplete="new-password" placeholder="Paste your provider key" minLength={8} maxLength={512} required /></label>
                <button className="solo-primary-button" type="submit" disabled={credentialSaving || !credentialLabel.trim() || !credentialKey}>{credentialSaving ? <><span className="spinner" /> Validating…</> : <><Icon name="plus" /> Connect provider</>}</button>
              </form>
            </section>
            <section className="solo-settings-card"><div className="solo-card-heading"><div><h2>Connected credentials</h2><p>Multiple credentials per provider are supported.</p></div><span className="solo-count">{credentials.length}</span></div>
              {credentials.length ? <div className="solo-credential-list">{credentials.map((credential) => <article className="solo-credential" key={credential.id}>
                {editCredentialId === credential.id ? <form className="solo-credential-edit" onSubmit={(event) => void saveCredentialEdit(event)}>
                  <label>Name<input value={editLabel} onChange={(event) => setEditLabel(event.target.value)} maxLength={80} required /></label>
                  <label>Replace key <span>(leave blank to keep current)</span><input type="password" value={editKey} onChange={(event) => setEditKey(event.target.value)} autoComplete="new-password" minLength={8} maxLength={512} /></label>
                  <div><button className="solo-secondary-button" type="button" onClick={() => setEditCredentialId(null)}>Cancel</button><button className="solo-primary-button" type="submit" disabled={credentialSaving}>Save changes</button></div>
                </form> : <>
                  <span className="solo-provider-icon"><Icon name="key" /></span><div className="solo-credential-info"><strong>{credential.label}</strong><span>{credential.provider} · •••• {credential.key_suffix}</span><small className={credential.status === "active" ? "status-ready" : "status-failed"}>{credential.status === "active" ? "Connected" : "Needs attention"}</small></div>
                  <div className="solo-credential-actions"><button type="button" onClick={() => { setEditCredentialId(credential.id); setEditLabel(credential.label); setEditKey("") }}>Edit</button><button type="button" onClick={() => void setAsDefault(credential)}>Set default</button><button type="button" className="text-danger" onClick={() => void removeCredential(credential)}>Remove</button></div>
                  {preferences.credential_id === credential.id && <span className="solo-default-tag">Default</span>}
                </>}
              </article>)}</div> : <div className="solo-inline-empty"><Icon name="key" /><p>No providers connected yet. Your API key stays private to your account.</p></div>}
            </section>
            <p className="solo-security-note"><Icon name="shield" /> Keys are encrypted server-side. Only metadata and the last four characters are visible here.</p>
          </main> : <main className="solo-settings-page">
            <div className="solo-page-heading"><p className="solo-eyebrow">PRIVATE KNOWLEDGE</p><h1>Knowledge sources</h1><p>Add personal documents and public links to ground your AI conversations in information you trust.</p></div>
            <section className="solo-source-actions">
              <button className="solo-upload-card" type="button" onClick={() => fileRef.current?.click()} disabled={sourceBusy}>
                <span className="solo-upload-icon"><Icon name="upload" /></span><strong>{sourceBusy ? "Processing source…" : "Upload a document"}</strong><span>PDF, TXT, or Markdown · up to 10 MB</span><span className="solo-secondary-button">Choose file</span>
              </button>
              <form className="solo-url-card" onSubmit={(event) => void addUrl(event)}>
                <span className="solo-upload-icon"><Icon name="link" /></span><strong>Add a public URL</strong><span>We’ll extract readable text from the page.</span>
                <label className="visually-hidden" htmlFor="source-url">Web address</label><div><input id="source-url" type="url" value={urlDraft} onChange={(event) => setUrlDraft(event.target.value)} placeholder="https://example.com/article" required /><button className="solo-primary-button" type="submit" disabled={sourceBusy || !urlDraft.trim()} aria-label="Add URL">{sourceBusy ? <span className="spinner" /> : <Icon name="arrow" />}</button></div>
              </form>
              <input ref={fileRef} className="visually-hidden" type="file" aria-label="Upload a document" accept=".pdf,.txt,.md,.markdown,application/pdf,text/plain,text/markdown" onChange={(event) => void uploadFile(event.target.files?.[0])} />
            </section>
            <section className="solo-settings-card solo-sources-card"><div className="solo-card-heading"><div><h2>Your sources</h2><p>Only you can access these files and their extracted content.</p></div><span className="solo-count">{sources.length}</span></div>
              {sources.length ? <div className="solo-source-list">{sources.map((source) => <article className="solo-source-row" key={source.id}>
                <span className="solo-source-icon"><Icon name={source.kind === "url" ? "link" : "file"} /></span><div className="solo-source-info"><strong>{source.title}</strong><span>{source.kind === "url" ? source.url : `${source.mime_type ?? "Document"} · ${Math.ceil((source.size_bytes ?? 0) / 1024)} KB`}</span></div>
                <span className={`solo-source-status solo-source-status--${source.status}`}><i />{source.status === "ready" ? "Ready" : source.status === "processing" ? "Processing" : "Could not process"}</span>
                <button type="button" className="solo-source-remove" aria-label={`Remove ${source.title}`} onClick={() => void removeSource(source)}><Icon name="close" /></button>
              </article>)}</div> : <div className="solo-sources-empty"><span className="solo-empty-mark"><Icon name="knowledge" /></span><h2>No sources yet</h2><p>Upload a document or add a public URL. When processing succeeds, your conversations can use the source as context.</p></div>}
            </section>
            <p className="solo-security-note"><Icon name="shield" /> Source content is private to your Solo workspace. Unsupported files and unsafe URLs are rejected.</p>
          </main>}
      </div>
      {deleteTarget && <div className="solo-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDeleteTarget(null) }}>
        <section className="solo-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-title"><span className="solo-dialog-icon"><Icon name="trash" /></span><h2 id="delete-title">Delete conversation?</h2><p>“{deleteTarget.title}” and its message history will be permanently removed.</p><div><button className="solo-secondary-button" type="button" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</button><button className="solo-danger-button" type="button" onClick={() => void confirmDeleteConversation()} disabled={deleting}>{deleting ? "Deleting…" : "Delete conversation"}</button></div></section>
      </div>}
    </div>
  )
}
