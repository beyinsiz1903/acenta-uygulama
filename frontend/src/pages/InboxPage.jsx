import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { getUser } from "../lib/api";
import { listInboxThreads, listInboxMessages, createInboxMessage } from "../lib/inbox";
import { Button } from "../components/ui/button";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Loader2 } from "lucide-react";

function useQuery() {
  const { search } = useLocation();
  return React.useMemo(() => new URLSearchParams(search), [search]);
}

function InboxPage() {
  const user = getUser();
  const query = useQuery();
  const initialBookingId = query.get("booking_id") || "";

  const [threads, setThreads] = useState([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [threadsError, setThreadsError] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [searchQ, setSearchQ] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [selectedThreadId, setSelectedThreadId] = useState("");

  const [messages, setMessages] = useState([]);
  const [messagesTotal, setMessagesTotal] = useState(0);
  const [messagesPage, setMessagesPage] = useState(1);
  const [messagesPageSize] = useState(50);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [errMessages, setErrMessages] = useState("");

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
      if (!selectedThreadId && items.length > 0) {
        setSelectedThreadId(items[0].id);
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
          {threadsLoading && (
            <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Inbox yükleniyor...
            </div>
          )}

          {!threadsLoading && threadsError && (
            <div className="p-4">
              <ErrorState
                title="Inbox yüklenemedi"
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
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {t.last_message_at || ""}
                  </p>
                  <p
                    className="text-[11px] text-muted-foreground mt-0.5"
                    data-testid="inbox-thread-count"
                  >
                    {t.message_count ?? 0} mesaj
                  </p>
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
            <div className="p-3 border-b">
              <h2 className="text-sm font-semibold">
                {threadDetail?.thread?.subject || "Thread"}
              </h2>
              {threadDetail?.thread?.booking_id && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  Booking: {threadDetail.thread.booking_id}
                </p>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {detailLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Mesajlar yükleniyor...
                </div>
              )}

              {!detailLoading && detailError && (
                <ErrorState
                  title="Thread yüklenemedi"
                  description={detailError}
                  onRetry={() => loadThreadDetail(selectedThreadId)}
                />
              )}

              {!detailLoading && !detailError && threadDetail && (
                <div className="space-y-2 text-sm">
                  {threadDetail.messages.map((m) => (
                    <div
                      key={m.id}
                      className={`max-w-[80%] px-3 py-2 rounded-2xl border text-sm whitespace-pre-wrap ${
                        m.sender_type === "SYSTEM"
                          ? "bg-muted text-muted-foreground border-muted/60"
                          : "bg-primary/5 text-foreground border-primary/20 ml-auto"
                      }`}
                    >
                      {m.event_type && (
                        <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">
                          {m.event_type}
                        </div>
                      )}
                      <div>{m.body}</div>
                      {m.sender_email && (
                        <div className="mt-1 text-[10px] text-muted-foreground">
                          {m.sender_email}
                        </div>
                      )}
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
                  onChange={(e) => setNewMessage(e.target.value)}
                />
                <Button type="submit" size="sm" disabled={sendLoading || !newMessage.trim()}>
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

export default InboxPage;
