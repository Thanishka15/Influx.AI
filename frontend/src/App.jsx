import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link, NavLink, Outlet, Route, Routes, useNavigate, useOutletContext } from "react-router-dom";
import remarkGfm from "remark-gfm";

const API = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const STORAGE_KEYS = {
  activeConversation: "influx-ai-active-conversation",
  conversations: "influx-ai-conversations",
  userId: "influx-ai-user-id",
  legacyConversation: "influx-ai-cid",
  legacyMessages: "influx-ai-msg",
};
const uid = () => crypto.randomUUID();
const userId = () => {
  const stored = localStorage.getItem(STORAGE_KEYS.userId);
  if (stored) return stored;
  const id = uid();
  localStorage.setItem(STORAGE_KEYS.userId, id);
  return id;
};
const conversationTitle = (messages) => {
  const firstUserMessage = messages.find((message) => message.role === "user")?.content?.trim();
  return firstUserMessage ? `${firstUserMessage.slice(0, 42)}${firstUserMessage.length > 42 ? "…" : ""}` : "New conversation";
};
const newConversation = () => ({ id: uid(), title: "New conversation", messages: [], updatedAt: Date.now() });

function savedConversations() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEYS.conversations) || "[]");
    if (Array.isArray(stored) && stored.length) return stored.filter((item) => item && typeof item.id === "string" && Array.isArray(item.messages));
  } catch { /* Use the existing single-chat data below. */ }
  try {
    const messages = JSON.parse(sessionStorage.getItem(STORAGE_KEYS.legacyMessages) || "[]");
    if (Array.isArray(messages) && messages.length) {
      return [{ id: sessionStorage.getItem(STORAGE_KEYS.legacyConversation) || uid(), title: conversationTitle(messages), messages, updatedAt: Date.now() }];
    }
  } catch { /* Start with a fresh conversation. */ }
  return [newConversation()];
}

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : `Request failed (${response.status}).`);
  }
  return payload;
}

const I = ({ children }) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{children}</svg>;
const Spark = () => <I><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" /></I>;
const icon = {
  chat: <I><path d="M20 15a4 4 0 0 1-4 4H8l-4 3V7a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4Z" /><path d="M8 10h8M8 14h5" /></I>,
  memory: <I><path d="M12 5a3 3 0 0 0-5.5 1.7A3.5 3.5 0 0 0 7 13.5V16a3 3 0 0 0 5 2.2A3 3 0 0 0 17 16v-2.5a3.5 3.5 0 0 0 .5-6.8A3 3 0 0 0 12 5v14M8 10h4M12 10h4" /></I>,
  analytics: <I><path d="M4 19V5M4 19h17" /><path d="m7 15 4-4 3 2 5-6" /></I>,
};

function cleanAssistantMarkdown(content) {
  const normalized = content
    .replace(/\r\n?/g, "\n")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<br\s*\/?\s*>/gi, "\n")
    .replace(/<\/?[a-z][^>]*>/gi, "")
    .replace(/^```(?:markdown|md|text|plaintext)?\s*$/gim, "")
    .trim();
  return normalized.split("\n").map((line) => {
    const markers = line.match(/\*{2,3}/g) || [];
    return markers.length % 2 ? line.replace(/\*{2,3}/g, "") : line;
  }).join("\n");
}

function profileFromSavedReplies(conversations) {
  const marker = /<!--\s*INFLUX_PROFILE\s*:\s*(\{[\s\S]*?\})\s*-->/gi;
  return conversations.reduce((profile, conversation) => {
    conversation.messages.forEach((message) => {
      if (message.role !== "assistant" || typeof message.content !== "string") return;
      for (const match of message.content.matchAll(marker)) {
        try { Object.assign(profile, JSON.parse(match[1])); } catch { /* Ignore malformed legacy markers. */ }
      }
    });
    return profile;
  }, {});
}

function AssistantMessage({ content }) {
  return <div className="assistant-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: ({ children }) => <div className="markdown-table-scroll"><table>{children}</table></div> }}>{cleanAssistantMarkdown(content)}</ReactMarkdown></div>;
}

function Layout({ context }) {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const fresh = () => { context.createConversation(); navigate("/"); setIsOpen(false); };
  const openConversation = (id) => { context.selectConversation(id); navigate("/"); setIsOpen(false); };
  const removeConversation = (id, title) => {
    if (window.confirm(`Delete “${title}”? This cannot be undone.`)) context.deleteConversation(id);
  };
  return <div className="shell">
    <button aria-label="Close navigation" className={`scrim ${isOpen ? "visible" : ""}`} onClick={() => setIsOpen(false)} />
    <aside className={isOpen ? "open" : ""}>
      <div className="brand"><span><Spark /></span>Influx.AI<button aria-label="Close navigation" onClick={() => setIsOpen(false)}>×</button></div>
      <button className="new" onClick={fresh}>＋ New conversation</button>
      <nav>
        <NavLink end to="/" onClick={() => setIsOpen(false)}>{icon.chat}Chat</NavLink>
        <section className="conversation-history" aria-label="Conversations">
          <label>RECENT CONVERSATIONS</label>
          <div className="conversation-history-list">{context.conversations.map((conversation) => <div className={`conversation-history-item ${conversation.id === context.conversationId ? "active" : ""}`} key={conversation.id}><button className="conversation-select" onClick={() => openConversation(conversation.id)} title={conversation.title}>{conversation.title}</button><button aria-label={`Delete ${conversation.title}`} className="conversation-delete" onClick={() => removeConversation(conversation.id, conversation.title)}>×</button></div>)}</div>
        </section>
        <NavLink to="/memory" onClick={() => setIsOpen(false)}>{icon.memory}Memory</NavLink>
        <NavLink to="/analytics" onClick={() => setIsOpen(false)}>{icon.analytics}Analytics</NavLink>
      </nav>
      <div className="profile"><div>I</div><p><strong>Creator workspace</strong></p></div>
    </aside>
    <button aria-label="Open navigation" className="menu" onClick={() => setIsOpen(true)}>☰</button>
    <Outlet context={context} />
  </div>;
}

function Chat() {
  const { conversationId, messages, setMessages, userId } = useOutletContext();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef();
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);
  async function send(event) {
    event.preventDefault();
    const message = text.trim();
    if (!message || busy) return;
    setMessages((items) => [...items, { id: uid(), role: "user", content: message }]);
    setText(""); setBusy(true); setError("");
    try {
      const data = await request("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, conversation_id: conversationId, user_id: userId }) });
      if (typeof data.reply !== "string" || !data.reply.trim()) throw new Error("Influx.AI returned an empty reply.");
      setMessages((items) => [...items, { id: uid(), role: "assistant", content: data.reply }]);
    } catch (caught) { setError(caught.message || "Unable to reach Influx.AI."); } finally { setBusy(false); }
  }
  return <main className="chat page"><header><div><label>SOCIAL MEDIA ENGAGEMENT AGENT</label><h1>Influx.AI <span>✦</span></h1><p>Turn content insights into consistent growth</p></div><p className="status">● Memory active</p></header><section className="remember"><span>{icon.memory}</span><p>Every conversation can improve your next recommendation.</p><Link to="/memory">View memory →</Link></section><div className="conversation">{!messages.length && <div className="empty-chat"><span><Spark /></span><h2>Start with your creator context</h2><p>Tell Influx.AI about your audience, niche, voice, or results.</p></div>}{messages.map((message) => <article className={message.role === "assistant" ? "ai" : "you"} key={message.id}>{message.role === "assistant" && <span className="bot"><Spark /></span>}<div><label>{message.role === "assistant" ? "INFLUX.AI" : "YOU"}</label>{message.role === "assistant" ? <AssistantMessage content={message.content} /> : <p>{message.content}</p>}</div></article>)}{busy && <article className="ai"><span className="bot"><Spark /></span><div><label>INFLUX.AI</label><p className="dots">•••</p></div></article>}<div ref={bottom} /></div>{error && <p className="api-error" role="alert">{error}</p>}<form className="composer" onSubmit={send}><input disabled={busy} value={text} onChange={(event) => setText(event.target.value)} placeholder="Tell Influx.AI about your creator strategy..." /><button aria-label="Send message" disabled={busy || !text.trim()}>➤</button></form></main>;
}

const fields = [["👥", "Audience", "audience"], ["◌", "Niche", "niche"], ["◷", "Posting time", "posting_time"], ["✦", "Tone", "tone"], ["文", "Language", "language"], ["◉", "Preferred format", "preferred_format"]];
function ErrorState({ error, retry }) { return <section className="error-state"><h2>Couldn’t load live data</h2><p>{error}</p><button className="save" onClick={retry}>Try again</button></section>; }
function Memory() {
  const [data, setData] = useState(); const [error, setError] = useState("");
  const { userId } = useOutletContext();
  const load = useCallback(async () => { setError(""); try { setData(await request(`/memory?user_id=${encodeURIComponent(userId)}`)); } catch (caught) { setError(caught.message); } }, [userId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  if (!data && !error) return <main className="page loading">Loading creator memory…</main>;
  if (error) return <main className="page"><ErrorState error={error} retry={load} /></main>;
  const profile = data.profile || {};
  return <main className="page dashboard"><header><div><label>YOUR LONG-TERM CONTEXT</label><h1>Memory dashboard <span>✦</span></h1><p>The creator memory powering every future recommendation.</p></div><button className="refresh" onClick={load}>Refresh</button></header><section className="memory-stats"><span><b>{data.count ?? 0}</b> creator memories and </span><span><b>{data.analytics_count ?? 0}</b> learned insights</span></section><section className="cards">{fields.map(([symbol, title, key]) => <div className="card" key={key}><i>{symbol}</i><label>{title}</label><h3>{profile[key] || "Not learned yet"}</h3><p>Last updated: {profile.last_updated || "Not learned yet"}</p></div>)}</section><section className="panel"><div className="title"><div><label>MEMORY SUMMARY</label><h2>What Influx.AI knows</h2></div></div><p className="summary-copy">{profile.summary || "No creator preferences have been learned yet."}</p>{data.latest_memory && <div className="latest-memory">{data.latest_memory.text || data.latest_memory.content || "Latest memory stored."}</div>}</section></main>;
}

function EngagementTrend({ entries }) {
  if (!entries.length) return null;
  const values = entries.slice(0, 8).reverse().map((entry) => entry.total_engagement || 0);
  const high = Math.max(...values, 1);
  const low = Math.min(...values, 0);
  const range = Math.max(high - low, 1);
  const points = values.map((value, index) => {
    const x = values.length === 1 ? 140 : 10 + (index * 260) / (values.length - 1);
    const y = 76 - ((value - low) / range) * 54;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const area = `10,86 ${points} 270,86`;
  return <section className="engagement-trend" aria-label="Engagement trend from recent saved posts"><div className="trend-heading"><span>ENGAGEMENT TREND</span><b>{values.at(-1)}</b></div><svg viewBox="0 0 280 105" role="img" aria-label={`Engagement trend across ${values.length} recent posts`}><title>Engagement trend</title><defs><linearGradient id="engagement-fill" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#a280ff" stopOpacity=".38" /><stop offset="1" stopColor="#8b5cf6" stopOpacity="0" /></linearGradient></defs><path className="trend-grid" d="M10 24H270M10 50H270M10 76H270" /><polygon fill="url(#engagement-fill)" points={area} /><polyline className="trend-line" points={points} />{points.split(" ").map((point, index) => <circle className="trend-point" cx={point.split(",")[0]} cy={point.split(",")[1]} key={point} r={index === values.length - 1 ? "3.5" : "2.2"} />)}<text x="10" y="101">Earlier</text><text x="236" y="101">Latest</text></svg></section>;
}

function Analytics() {
  const [data, setData] = useState(); const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [form, setForm] = useState({ post_type: "Reel", likes: "", comments: "", shares: "" });
  const { userId } = useOutletContext();
  const load = useCallback(async () => { try { setData(await request(`/analytics?user_id=${encodeURIComponent(userId)}`)); } catch (caught) { setError(caught.message); } }, [userId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function save(event) { event.preventDefault(); setBusy(true); setError(""); try { await request("/analytics", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, user_id: userId, likes: Number(form.likes), comments: Number(form.comments), shares: Number(form.shares) }) }); setForm({ post_type: "Reel", likes: "", comments: "", shares: "" }); await load(); } catch (caught) { setError(caught.message); } finally { setBusy(false); } }
  const summary = data?.summary; const entries = Array.isArray(data?.items) ? data.items : [];
  return <main className="page dashboard"><header><div><label>MANUAL PERFORMANCE LOG</label><h1>Content analytics <span>✦</span></h1><p>Learn what works from every post you log.</p></div></header><div className="split"><section className="panel log"><div className="title"><h2>Log a post</h2></div><form onSubmit={save}><label>Post type<select value={form.post_type} onChange={(event) => setForm({ ...form, post_type: event.target.value })}><option>Reel</option><option>Carousel</option><option>Static post</option><option>Story</option></select></label><div className="fields">{["likes", "comments", "shares"].map((key) => <label key={key}>{key}<input required min="0" type="number" value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}</div><button className="save" disabled={busy}>{busy ? "Saving…" : "Save performance →"}</button></form></section><section className="insight"><label>CURRENT INSIGHT</label>{summary?.total_entries ? <><h2>{summary.best_format} is your strongest format.</h2><p>{summary.insight}</p><div className="insight-stat"><b>{summary.average_engagement}</b><span>average engagement<br />across {summary.total_entries} posts</span></div><EngagementTrend entries={entries} /></> : <><h2>Insights appear after your first post.</h2><p>Log real performance to compare formats.</p></>}</section></div>{error && <p className="api-error" role="alert">{error}</p>}<section className="panel table"><div className="title"><h2>Saved entries</h2><button className="refresh" onClick={load}>Refresh</button></div>{!data ? <p className="empty">Loading analytics…</p> : !entries.length ? <p className="empty">No analytics saved yet.</p> : <div className="table-scroll"><table><thead><tr><th>Post</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Total</th><th>Logged</th></tr></thead><tbody>{entries.map((entry, index) => <tr key={entry.id || index}><td><mark>{entry.post_type}</mark></td><td>{entry.likes}</td><td>{entry.comments}</td><td>{entry.shares}</td><td><b>{entry.total_engagement}</b></td><td>{entry.posted_at && !Number.isNaN(Date.parse(entry.posted_at)) ? new Date(entry.posted_at).toLocaleDateString() : "—"}</td></tr>)}</tbody></table></div>}</section></main>;
}

export default function App() {
  const [currentUserId] = useState(userId);
  const [conversations, setConversations] = useState(savedConversations);
  const recoveredProfile = useRef("");
  const [conversationId, setConversationId] = useState(() => localStorage.getItem(STORAGE_KEYS.activeConversation) || conversations[0].id);
  const activeConversation = conversations.find((conversation) => conversation.id === conversationId) || conversations[0];
  const activeConversationId = activeConversation.id;
  const messages = activeConversation.messages;
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.conversations, JSON.stringify(conversations));
    localStorage.setItem(STORAGE_KEYS.activeConversation, activeConversationId);
  }, [activeConversationId, conversations]);
  useEffect(() => {
    const profile = profileFromSavedReplies(conversations);
    const signature = JSON.stringify(profile);
    if (!signature || signature === "{}" || recoveredProfile.current === signature) return;
    recoveredProfile.current = signature;
    void request("/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: currentUserId, profile }) }).catch(() => {});
  }, [conversations, currentUserId]);
  const setMessages = (update) => setConversations((items) => items.map((conversation) => {
    if (conversation.id !== activeConversationId) return conversation;
    const nextMessages = typeof update === "function" ? update(conversation.messages) : update;
    return { ...conversation, messages: nextMessages, title: conversationTitle(nextMessages), updatedAt: Date.now() };
  }));
  const createConversation = () => {
    const conversation = newConversation();
    setConversations((items) => [conversation, ...items]);
    setConversationId(conversation.id);
  };
  const selectConversation = (id) => {
    if (conversations.some((conversation) => conversation.id === id)) setConversationId(id);
  };
  const deleteConversation = (id) => {
    const remaining = conversations.filter((conversation) => conversation.id !== id);
    if (!remaining.length) {
      const conversation = newConversation();
      setConversations([conversation]);
      setConversationId(conversation.id);
      return;
    }
    setConversations(remaining);
    if (id === activeConversationId) setConversationId(remaining[0].id);
  };
  const context = { conversationId: activeConversationId, conversations, messages, setMessages, createConversation, selectConversation, deleteConversation, userId: currentUserId };
  return <Routes><Route element={<Layout context={context} />}><Route index element={<Chat />} /><Route path="memory" element={<Memory />} /><Route path="analytics" element={<Analytics />} /></Route></Routes>;
}
