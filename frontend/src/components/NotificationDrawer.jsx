import React, { useEffect, useState } from 'react';
import { X, Bell, Activity, AlertTriangle, Clock, ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { Skeleton } from './ui/skeleton';

/* ------------------------------------------------------------------ */
/*  Event row                                                           */
/* ------------------------------------------------------------------ */
function EventRow({ item }) {
  const time = item.created_at
    ? new Date(item.created_at).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })
    : '';

  return (
    <div className="flex gap-3 py-2.5 border-b border-border/30 last:border-b-0 group">
      <div className="h-7 w-7 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0 mt-0.5">
        <Activity className="h-3.5 w-3.5 text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-foreground truncate">
          {item.action || item.type || 'Bilinmeyen olay'}
        </p>
        <p className="text-xs text-muted-foreground truncate">
          {item.actor?.email || item.actor?.name || ''}
          {item.target?.type ? ` → ${item.target.type}` : ''}
          {item.target?.id ? ` #${item.target.id.slice(0, 8)}` : ''}
        </p>
        <p className="text-2xs text-muted-foreground/60 mt-0.5">{time}</p>
      </div>
    </div>
  );
}

/* ================================================================== */
/*  NOTIFICATION DRAWER                                                */
/* ================================================================== */
export default function NotificationDrawer({ open, onClose }) {
  const [tab, setTab] = useState('activities');
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.get('/audit/logs', { params: { range: '7d', limit: 30 } });
        if (!cancelled) setEvents(res.data || []);
      } catch {
        // audit endpoint may require super_admin; graceful
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [open]);

  if (!open) return null;

  const activities = events;
  const alerts = []; // No alert endpoint yet

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-50 transition-opacity"
        onClick={onClose}
      />
      {/* Drawer */}
      <div
        className="fixed right-0 top-0 bottom-0 w-[380px] max-w-[90vw] bg-card border-l border-border z-50 flex flex-col shadow-xl"
        data-testid="notif-drawer"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-foreground">Bildirimler</span>
          </div>
          <button
            onClick={onClose}
            className="h-7 w-7 rounded-md flex items-center justify-center hover:bg-muted/50 transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setTab('activities')}
            className={`flex-1 px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
              tab === 'activities'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Aktiviteler
          </button>
          <button
            onClick={() => setTab('alerts')}
            className={`flex-1 px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
              tab === 'alerts'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Uyarılar
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          {tab === 'activities' && (
            <>
              {loading ? (
                <div className="space-y-4 mt-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex gap-3">
                      <Skeleton className="h-7 w-7 rounded-full shrink-0" />
                      <div className="flex-1 space-y-1.5">
                        <Skeleton className="h-3 w-full" />
                        <Skeleton className="h-2.5 w-2/3" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : activities.length > 0 ? (
                activities.map((ev, i) => <EventRow key={ev.id || ev._id || i} item={ev} />)
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                    <Clock className="h-5 w-5 text-muted-foreground/50" />
                  </div>
                  <p className="text-sm text-muted-foreground">Henüz aktivite yok</p>
                  <p className="text-xs text-muted-foreground/60 mt-0.5">Son 7 günde kayıtlı olay bulunamadı</p>
                </div>
              )}
            </>
          )}

          {tab === 'alerts' && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                <AlertTriangle className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-sm text-muted-foreground">Aktif uyarı yok</p>
              <p className="text-xs text-muted-foreground/60 mt-0.5">Kritik uyarılar burada görünecek</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
