import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { getUser } from "../lib/api";
import { listInboxThreads, listInboxMessages, createInboxMessage, updateInboxThreadStatus } from "../lib/inbox";
import { Button } from "../components/ui/button";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

function useQuery() {
  const { search } = useLocation();
  return React.useMemo(() => new URLSearchParams(search), [search]);
}

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString();
  } catch (e) {
    return String(value);
  }
}


function InboxPage() {
  const user = getUser();
  const query = useQuery();
  const initialBookingId = query.get("booking_id") || "";
  const initialThreadId = query.get("thread") || "";

  const [threads, setThreads] = useState([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [threadsError, setThreadsError] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [searchQ, setSearchQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [selectedThreadId, setSelectedThreadId] = useState(initialThreadId || "");

  const [messages, setMessages] = useState([]);
  const [messagesTotal, setMessagesTotal] = useState(0);
  const [messagesPage, setMessagesPage] = useState(1);
  const [messagesPageSize] = useState(50);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [errMessages, setErrMessages] = useState("");

  const [threadErrorShown, setThreadErrorShown] = useState(false);
  const [threadNotFound, setThreadNotFound] = useState(false);

  const [newMessage, setNewMessage] = useState("");
  const [sendLoading, setSendLoading] = useState(false);

  const isAllowed = useMemo(() => {
    const roles = (user && user.roles) || [];
    return roles.includes("admin") || roles.includes("super_admin") || roles.includes("ops");
  }, [user]);

  const hasMoreThreads = threads.length < total;
  const hasMoreMessages = messages.length < messagesTotal;

  const loadThreads = async (opts = {}) => {
    if (!isAllowed) return;
    const reset = opts.reset || false;
    const effectivePage = reset ? 1 : page;

    setThreadsLoading(true);
    setThreadsError("");

    try {
      const res = await listInboxThreads({
        status: statusFilter || undefined,
        q: searchQ || undefined,
        page: effectivePage,
        pageSize,
      });
      const items = res.items || [];
      if (reset) {
        setThreads(items);
      } else {
        setThreads((prev) => [...prev, ...items]);
      }
      setTotal(res.total || 0);
      setPage(res.page || effectivePage);

      if (items.length > 0) {
        // Deep-link: if initialThreadId is present
        if (initialThreadId && !selectedThreadId) {
          const exists = items.some((t) => t.id === initialThreadId);
          if (exists) {
            setSelectedThreadId(initialThreadId);
          } else if (!threadErrorShown) {
            // Only show once
            toast.error("Thread bulunamadı veya erişim yok.");
            setThreadErrorShown(true);
            setThreadNotFound(true);
            setSelectedThreadId(items[0].id);
          }
        } else if (!initialThreadId && !selectedThreadId) {
          // Default behaviour: select first thread if nothing selected and no deep-link
          setSelectedThreadId(items[0].id);
        }
      }
    } catch (e) {
      setThreadsError(e.message || "Inbox y\u00fcklenemedi.");
      if (reset) setThreads([]);
    } finally {
      setThreadsLoading(false);
    }
  };

  const loadMessages = async (threadId, opts = {}) => {
    if (!isAllowed || !threadId) return;
    const reset = opts.reset || false;
    const effectivePage = reset ? 1 : messagesPage;

    setLoadingMessages(true);
    setErrMessages("");
    try {
      const res = await listInboxMessages(threadId, {
        page: effectivePage,
        pageSize: messagesPageSize,
      });
      const items = res.items || [];
      if (reset) {
        setMessages(items);
      } else {
        setMessages((prev) => [...prev, ...items]);
      }
      setMessagesTotal(res.total || 0);
      setMessagesPage(res.page || effectivePage);
    } catch (e) {
      setErrMessages(e.message || "Mesajlar y\u00fcklenemedi.");
      if (reset) setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  useEffect(() => {
    if (!isAllowed) return;
    loadThreads({ reset: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, searchQ, isAllowed]);

  useEffect(() => {
    if (!isAllowed) return;
    if (selectedThreadId) {
      loadMessages(selectedThreadId, { reset: true });
    } else {
      setMessages([]);
      setMessagesTotal(0);
      setMessagesPage(1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedThreadId, isAllowed]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedThreadId || !isAllowed) return;

    setSendLoading(true);
    try {
      await createInboxMessage(selectedThreadId, {
        direction: "internal",
        body: newMessage.trim(),
        attachments: [],
      });
      setNewMessage("");
      // Refresh messages and threads deterministically
      await loadMessages(selectedThreadId, { reset: true });
      await loadThreads({ reset: true });
    } catch (e) {
      setErrMessages(e.message || "Mesaj g\u00f6nderilemedi.");
    } finally {
      setSendLoading(false);
    }
  };

  if (!isAllowed) {
    return (
      <div className="p-4">
        <ErrorState
          title="Erişim kısıtlı"
          description="Bu sayfaya yalnızca admin/ops kullanıcılar erişebilir."
        />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-64px)] flex">
      {/* Thread list */}
      <div className="w-full md:w-1/3 border-r bg-background flex flex-col">
        <div className="p-3 border-b flex items-center justify-between gap-2">
          <div className="flex gap-1 text-xs">
            {[
              ["open", "Açık"],
              ["pending", "Beklemede"],
              ["done", "Tamamlandı"],
              ["", "Hepsi"],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatusFilter(value)}
                className={`px-2 py-1 rounded-full border text-xs ${
                  statusFilter === value
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-muted text-muted-foreground"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {threadNotFound && (
            <div
              data-testid="inbox-thread-not-found"
              className="px-3 py-2 text-xs text-destructive bg-destructive/5 border-b border-destructive/30"
            >
              Thread bulunamadı veya erişim yok.
            </div>
          )}

          {threadsLoading && (
            <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Gelen kutusu yükleniyor...
            </div>
          )}

          {!threadsLoading && threadsError && (
            <div className="p-4">
              <ErrorState
                title="Gelen kutusu yüklenemedi"
                description={threadsError}
                onRetry={() => loadThreads()}
              />
            </div>
          )}

          {!threadsLoading && !threadsError && threads.length === 0 && (
            <div className="p-4">
              <EmptyState
                title="Herhangi bir thread yok"
                description="Henüz bu organizasyon için bir inbox kaydı oluşmamış."
              />
            </div>
          )}

          {!threadsLoading && !threadsError && threads.length > 0 && (
            <ul className="divide-y">
              {threads.map((t) => (
                <li
                  key={t.id}
                  data-testid="inbox-thread-row"
                  data-selected={selectedThreadId === t.id ? "true" : undefined}
                  className={`p-3 cursor-pointer text-sm hover:bg-muted/60 ${
                    selectedThreadId === t.id ? "bg-muted" : ""
                  }`}
                  onClick={() => setSelectedThreadId(t.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="font-medium truncate max-w-[70%]"
                      data-testid="inbox-thread-subject"
                    >
                      {t.subject || "(Konu yok)"}
                    </span>
                    <span className="text-[10px] uppercase text-muted-foreground">
                      {t.channel || t.type || "internal"}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-2">
                    <p className="text-[11px] text-muted-foreground">
                      {formatDate(t.last_message_at)}
                    </p>
                    <span className="inline-flex items-center gap-1 rounded-full border bg-accent px-2 py-0.5 text-[10px] font-medium text-foreground/80">
                      <span>
                        {t.status === "open"
                          ? "Açık"
                          : t.status === "pending"
                          ? "Beklemede"
                          : t.status === "done"
                          ? "Tamamlandı"
                          : t.status || "Durum"}
                      </span>
                      <span className="text-foreground text-[10px]" data-testid="inbox-thread-count">
                        {t.message_count ?? 0} mesaj
                      </span>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Message panel */}
      <div className="hidden md:flex flex-1 flex-col bg-background">
        {!selectedThreadId && (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState
              title="Bir thread seçin"
              description="Soldaki listeden bir thread seçerek mesajları görüntüleyin."
            />
          </div>
        )}

        {selectedThreadId && (
          <div className="flex-1 flex flex-col">
            <div className="p-3 border-b flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">
                {selectedThreadId
                  ? threads.find((t) => t.id === selectedThreadId)?.subject || "Thread"
                  : "Thread"}
              </h2>
              {selectedThreadId && (
                <InboxThreadStatusControls
                  thread={threads.find((t) => t.id === selectedThreadId)}
                  onStatusChange={(nextStatus) => {
                    setThreads((prev) =>
                      prev.map((t) =>
                        t.id === selectedThreadId ? { ...t, status: nextStatus } : t
                      )
                    );
                  }}
                />
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {loadingMessages && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Mesajlar yükleniyor...
                </div>
              )}

              {!loadingMessages && errMessages && (
                <ErrorState
                  title="Mesajlar yüklenemedi"
                  description={errMessages}
                  onRetry={() => loadMessages(selectedThreadId, { reset: true })}
                />
              )}

              {!loadingMessages && !errMessages && messages.length === 0 && (
                <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
                  Bu thread için henüz mesaj yok.
                </div>
              )}

              {!loadingMessages && !errMessages && messages.length > 0 && (
                <div className="space-y-2 text-sm">
                  {messages.map((m) => (
                    <div
                      key={m.id}
                      data-testid="inbox-message-row"
                      className={`max-w-[80%] px-3 py-2 rounded-2xl border text-sm whitespace-pre-wrap ${
                        m.direction === "internal" ? "bg-primary/5 ml-auto" : "bg-muted"
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                        <span>{m.direction === "internal" ? "İç not" : "Dış mesaj"}</span>
                        <span>{formatDate(m.created_at)}</span>
                      </div>
                      <div>{m.body}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedThreadId && (
              <form onSubmit={handleSendMessage} className="border-t p-3 flex items-center gap-2">
                <textarea
                  className="flex-1 resize-none text-sm border rounded-lg px-2 py-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                  rows={2}
                  placeholder="Mesaj yazın..."
                  value={newMessage}
                  data-testid="inbox-compose-body"
                  onChange={(e) => setNewMessage(e.target.value)}
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={sendLoading || !newMessage.trim()}
                  data-testid="inbox-compose-send"
                >
                  {sendLoading ? "Gönderiliyor..." : "Gönder"}
                </Button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function InboxThreadStatusControls({ thread, onStatusChange }) {
  if (!thread) return null;
  const status = (thread.status || "open").toLowerCase();

  const labelMap = {
    open: "Açık",
    pending: "Beklemede",
    done: "Tamamlandı",
  };

  const handleUpdate = async (next) => {
    try {
      await updateInboxThreadStatus(thread.id, next);
      onStatusChange(next);
      toast.success("Durum güncellendi.");
    } catch (e) {
      toast.error(e.message || "Durum güncellenemedi.");
    }
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="px-2 py-1 rounded-full border border-muted text-muted-foreground">
        {labelMap[status] || status}
      </span>
      {status !== "open" && (
        <button
          type="button"
          className="px-2 py-1 border rounded-full text-xs hover:bg-muted"
          onClick={() => handleUpdate("open")}
        >
          Yeniden Aç
        </button>
      )}
      {status === "open" && (
        <>
          <button
            type="button"
            className="px-2 py-1 border rounded-full text-xs hover:bg-muted"
            onClick={() => handleUpdate("pending")}
          >
            Beklemeye Al
          </button>
          <button
            type="button"
            className="px-2 py-1 border rounded-full text-xs hover:bg-muted"
            onClick={() => handleUpdate("done")}
          >
            Tamamla
          </button>
        </>
      )}
    </div>
  );
}

export default InboxPage;
