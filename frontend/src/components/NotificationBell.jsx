import React, { useState, useEffect, useCallback, useRef } from "react";
import { Bell, Check, CheckCheck, ExternalLink, X } from "lucide-react";
import { api } from "../lib/api";
import { useNavigate } from "react-router-dom";

export default function NotificationBell() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  const loadNotifications = useCallback(async () => {
    try {
      const res = await api.get("/notifications?limit=15");
      setItems(res.data.items || []);
      setUnread(res.data.unread_count || 0);
    } catch {}
  }, []);

  const loadCount = useCallback(async () => {
    try {
      const res = await api.get("/notifications/unread-count");
      setUnread(res.data.unread_count || 0);
    } catch {}
  }, []);

  useEffect(() => {
    loadCount();
    const interval = setInterval(loadCount, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [loadCount]);

  useEffect(() => {
    if (open) loadNotifications();
  }, [open, loadNotifications]);

  // Click outside
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const markRead = async (id) => {
    try {
      await api.put(`/notifications/${id}/read`);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnread((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  const markAllRead = async () => {
    try {
      await api.put("/notifications/mark-all-read");
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } catch {}
  };

  const handleClick = (notif) => {
    if (!notif.is_read) markRead(notif.id);
    if (notif.link) {
      navigate(notif.link);
      setOpen(false);
    }
  };

  const typeColor = {
    quota_warning: "text-amber-500 bg-amber-50",
    payment_overdue: "text-rose-500 bg-rose-50",
    case_open: "text-blue-500 bg-blue-50",
    system: "text-muted-foreground bg-gray-50",
    b2b_match: "text-green-500 bg-green-50",
    payment_recorded: "text-green-500 bg-green-50",
    onboarding: "text-blue-500 bg-blue-50",
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-muted transition-colors"
        data-testid="notification-bell"
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 min-w-[16px] rounded-full bg-rose-500 text-white text-2xs font-bold flex items-center justify-center px-1" data-testid="unread-badge">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-slate-900 rounded-xl border shadow-xl z-50 overflow-hidden" data-testid="notification-dropdown">
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <h3 className="font-semibold text-sm">Bildirimler</h3>
            <div className="flex gap-1">
              {unread > 0 && (
                <button onClick={markAllRead} className="text-xs text-blue-600 hover:underline flex items-center gap-1" data-testid="mark-all-read">
                  <CheckCheck className="h-3.5 w-3.5" /> Tümünü oku
                </button>
              )}
              <button onClick={() => setOpen(false)} className="ml-2"><X className="h-4 w-4" /></button>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">Bildirim yok</div>
            )}
            {items.map((n) => (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-muted/30 transition-colors ${!n.is_read ? "bg-blue-50/50 dark:bg-blue-950/20" : ""}`}
              >
                <div className="flex gap-2">
                  <div className={`h-6 w-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${typeColor[n.type] || typeColor.system}`}>
                    <Bell className="h-3 w-3" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-medium truncate ${!n.is_read ? "text-foreground" : "text-muted-foreground"}`}>{n.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{n.message}</p>
                    <p className="text-2xs text-muted-foreground/60 mt-0.5">
                      {n.created_at ? new Date(n.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : ""}
                    </p>
                  </div>
                  {!n.is_read && <div className="h-2 w-2 rounded-full bg-blue-500 shrink-0 mt-1.5" />}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
