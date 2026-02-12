import React, { useState, useRef, useEffect, useCallback } from "react";
import { api, getToken } from "../lib/api";
import {
  Bot, X, Send, Sparkles, MessageCircle, RefreshCw,
  ChevronDown, Loader2, Zap, Calendar, Users, TrendingUp,
  Plus,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  AI Assistant - Floating Panel (Briefing + Chat)                    */
/* ------------------------------------------------------------------ */

const STORAGE_SESSION_KEY = "ai_assistant_session_id";

function getOrCreateSessionId() {
  let sid = localStorage.getItem(STORAGE_SESSION_KEY);
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
    localStorage.setItem(STORAGE_SESSION_KEY, sid);
  }
  return sid;
}

function newSession() {
  const sid = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  localStorage.setItem(STORAGE_SESSION_KEY, sid);
  return sid;
}

/* ---- Markdown-lite renderer ---- */
function renderMarkdown(text) {
  if (!text) return null;
  return text.split("\n").map((line, i) => {
    // Bold
    let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Bullet
    if (processed.trim().startsWith("- ") || processed.trim().startsWith("• ")) {
      return (
        <div key={i} className="flex items-start gap-1.5 ml-2 my-0.5">
          <span className="text-primary mt-1.5 shrink-0 text-[8px]">●</span>
          <span dangerouslySetInnerHTML={{ __html: processed.replace(/^[\-•]\s*/, "") }} />
        </div>
      );
    }
    // Heading-like lines
    if (processed.trim().startsWith("##") || processed.trim().startsWith("📋") || processed.trim().startsWith("💰") ||
        processed.trim().startsWith("👥") || processed.trim().startsWith("🏨") || processed.trim().startsWith("📬") ||
        processed.trim().startsWith("🔔") || processed.trim().startsWith("📊")) {
      return (
        <div key={i} className="font-semibold mt-2 mb-0.5 text-foreground">
          {processed.replace(/^##\s*/, "")}
        </div>
      );
    }
    // Empty line
    if (!processed.trim()) return <div key={i} className="h-1.5" />;
    // Normal
    return <div key={i} dangerouslySetInnerHTML={{ __html: processed }} />;
  });
}

/* ---- Briefing Card ---- */
function BriefingCard({ data, onRefresh, loading }) {
  if (!data) return null;
  const b = data.bookings || {};
  const crm = data.crm || {};
  const rev = data.revenue || [];
  const stats = [
    { icon: Calendar, label: "Bugünkü Rez.", value: b.today || 0, color: "text-blue-500" },
    { icon: Zap, label: "Bekleyen", value: b.pending || 0, color: "text-amber-500" },
    { icon: TrendingUp, label: "Onaylı", value: b.confirmed || 0, color: "text-emerald-500" },
    { icon: Users, label: "Açık Deal", value: crm.open_deals || 0, color: "text-purple-500" },
  ];

  return (
    <div className="bg-gradient-to-br from-primary/5 to-primary/10 rounded-xl p-3 mx-3 mt-3 border border-primary/20">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="text-[11px] font-semibold text-primary">Günlük Özet</span>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1 rounded-md hover:bg-primary/10 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 text-primary ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="bg-background/80 rounded-lg p-2 flex items-center gap-2">
            <s.icon className={`h-3.5 w-3.5 ${s.color}`} />
            <div>
              <div className="text-[10px] text-muted-foreground leading-none">{s.label}</div>
              <div className="text-sm font-bold leading-tight">{s.value}</div>
            </div>
          </div>
        ))}
      </div>
      {rev.length > 0 && (
        <div className="mt-2 bg-background/80 rounded-lg p-2">
          <div className="text-[10px] text-muted-foreground mb-0.5">💰 Toplam Gelir</div>
          {rev.map((r) => (
            <div key={r.currency} className="text-xs font-semibold">
              {Number(r.total_revenue).toLocaleString("tr-TR")} {r.currency}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Chat Message Bubble ---- */
function ChatBubble({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-[12.5px] leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-md"
            : "bg-muted text-foreground rounded-bl-md"
        }`}
      >
        {isUser ? content : renderMarkdown(content)}
      </div>
    </div>
  );
}

/* ---- Main Component ---- */
export default function AiAssistant() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("chat"); // "chat" | "briefing"
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [briefingText, setBriefingText] = useState("");
  const [briefingData, setBriefingData] = useState(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [sessionId, setSessionId] = useState(getOrCreateSessionId);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const hasToken = !!getToken();

  // Auto scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load chat history on session change
  useEffect(() => {
    if (!open || !hasToken) return;
    (async () => {
      try {
        const res = await api.get(`/ai-assistant/chat-history/${sessionId}`);
        if (res.data.messages && res.data.messages.length > 0) {
          setMessages(res.data.messages.map((m) => ({ role: m.role, content: m.content })));
        }
      } catch {
        // ignore
      }
    })();
  }, [sessionId, open, hasToken]);

  // Load briefing when panel opens
  const loadBriefing = useCallback(async () => {
    if (!hasToken) return;
    setBriefingLoading(true);
    try {
      const res = await api.post("/ai-assistant/briefing");
      setBriefingText(res.data.briefing || "");
      setBriefingData(res.data.raw_data || null);
    } catch (e) {
      setBriefingText("Brifing yüklenemedi. Lütfen tekrar deneyin.");
    } finally {
      setBriefingLoading(false);
    }
  }, [hasToken]);

  useEffect(() => {
    if (open && tab === "briefing" && !briefingText) {
      loadBriefing();
    }
  }, [open, tab, briefingText, loadBriefing]);

  // Send message
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);

    try {
      const res = await api.post("/ai-assistant/chat", {
        message: text,
        session_id: sessionId,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.response }]);
      if (res.data.session_id) {
        setSessionId(res.data.session_id);
        localStorage.setItem(STORAGE_SESSION_KEY, res.data.session_id);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin. 🔄" },
      ]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleNewSession = () => {
    const sid = newSession();
    setSessionId(sid);
    setMessages([]);
  };

  // Don't render if not logged in
  if (!hasToken) return null;

  return (
    <>
      {/* ---- Floating Button ---- */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-2xl hover:shadow-primary/25 hover:scale-105 transition-all duration-200 flex items-center justify-center group"
          data-testid="ai-assistant-btn"
        >
          <Bot className="h-6 w-6 group-hover:scale-110 transition-transform" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full border-2 border-background animate-pulse" />
        </button>
      )}

      {/* ---- Panel ---- */}
      {open && (
        <div
          className="fixed bottom-6 right-6 z-50 w-[380px] h-[580px] bg-background border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          data-testid="ai-assistant-panel"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-primary to-primary/80 px-4 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot className="h-4.5 w-4.5 text-white" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white leading-tight">Booking AI</div>
                <div className="text-[10px] text-white/70 leading-none">Akıllı Asistan</div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleNewSession}
                className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
                title="Yeni sohbet"
              >
                <Plus className="h-4 w-4 text-white" />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
              >
                <X className="h-4 w-4 text-white" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b shrink-0">
            <button
              onClick={() => setTab("chat")}
              className={`flex-1 py-2 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors ${
                tab === "chat"
                  ? "text-primary border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <MessageCircle className="h-3.5 w-3.5" /> Sohbet
            </button>
            <button
              onClick={() => setTab("briefing")}
              className={`flex-1 py-2 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors ${
                tab === "briefing"
                  ? "text-primary border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Sparkles className="h-3.5 w-3.5" /> Günlük Brifing
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {tab === "chat" ? (
              <div className="p-3 flex flex-col min-h-full">
                {messages.length === 0 && (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-3">
                      <Bot className="h-8 w-8 text-primary" />
                    </div>
                    <div className="text-sm font-semibold mb-1">Merhaba! 👋</div>
                    <div className="text-[11px] text-muted-foreground mb-4">
                      Booking AI olarak size yardımcı olmaya hazırım.
                      Rezervasyonlar, gelir, müşteriler hakkında sorular sorabilirsiniz.
                    </div>
                    <div className="grid grid-cols-1 gap-1.5 w-full">
                      {[
                        "Bugünkü rezervasyon özeti ne?",
                        "Bekleyen ödemeler var mı?",
                        "Bu haftaki gelir durumu nasıl?",
                      ].map((q) => (
                        <button
                          key={q}
                          onClick={() => {
                            setInput(q);
                            setTimeout(() => inputRef.current?.focus(), 50);
                          }}
                          className="text-left text-[11px] px-3 py-2 rounded-lg border border-border hover:bg-muted/50 hover:border-primary/30 transition-colors text-muted-foreground hover:text-foreground"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((m, i) => (
                  <ChatBubble key={i} role={m.role} content={m.content} />
                ))}

                {sending && (
                  <div className="flex justify-start mb-2">
                    <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-2.5 flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                      <span className="text-[11px] text-muted-foreground">Düşünüyorum...</span>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            ) : (
              <div className="p-0">
                {briefingLoading && !briefingData && (
                  <div className="flex flex-col items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-primary mb-3" />
                    <span className="text-[11px] text-muted-foreground">Brifing hazırlanıyor...</span>
                  </div>
                )}

                {briefingData && (
                  <BriefingCard
                    data={briefingData}
                    onRefresh={loadBriefing}
                    loading={briefingLoading}
                  />
                )}

                {briefingText && (
                  <div className="mx-3 mt-3 mb-3 bg-muted/50 rounded-xl p-3 text-[12px] leading-relaxed border">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      <span className="text-[11px] font-semibold">AI Brifing</span>
                    </div>
                    {renderMarkdown(briefingText)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Input (only for chat tab) */}
          {tab === "chat" && (
            <div className="border-t p-3 shrink-0 bg-background">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  sendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Mesajınızı yazın..."
                  disabled={sending}
                  className="flex-1 bg-muted rounded-xl px-3 py-2.5 text-[12.5px] outline-none focus:ring-2 focus:ring-primary/30 placeholder:text-muted-foreground/60 disabled:opacity-50"
                  data-testid="ai-chat-input"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || sending}
                  className="w-9 h-9 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                  data-testid="ai-chat-send"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          )}
        </div>
      )}
    </>
  );
}
