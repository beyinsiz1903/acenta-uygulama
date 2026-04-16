import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { CalendarDays, ChevronLeft, ChevronRight, Bus, Plane, FileCheck, Shield, MapPin, X, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";

const EVENT_COLORS = {
  transfer: "bg-blue-100 text-blue-800 border-blue-300",
  flight: "bg-sky-100 text-sky-800 border-sky-300",
  visa: "bg-purple-100 text-purple-800 border-purple-300",
  tour: "bg-orange-100 text-orange-800 border-orange-300",
  insurance: "bg-teal-100 text-teal-800 border-teal-300",
};

const EVENT_ICONS = {
  transfer: Bus,
  flight: Plane,
  visa: FileCheck,
  tour: MapPin,
  insurance: Shield,
};

const EVENT_LABELS = {
  transfer: "Transfer",
  flight: "U\u00e7u\u015f",
  visa: "Vize",
  tour: "Tur",
  insurance: "Sigorta",
};

function getMonthDays(year, month) {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days = [];
  const adjustedFirstDay = firstDay === 0 ? 6 : firstDay - 1;
  for (let i = 0; i < adjustedFirstDay; i++) days.push(null);
  for (let d = 1; d <= daysInMonth; d++) days.push(d);
  return days;
}

export default function AdminCalendarPage() {
  const navigate = useNavigate();
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [filterType, setFilterType] = useState("");
  const [detailModal, setDetailModal] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);

  const startDate = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const endDate = `${year}-${String(month + 1).padStart(2, "0")}-${new Date(year, month + 1, 0).getDate()}`;

  const { data, isLoading } = useQuery({
    queryKey: ["calendar-events", startDate, endDate, filterType],
    queryFn: () => {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
      if (filterType) params.set("event_type", filterType);
      return api.get(`/calendar/events?${params}`).then((r) => r.data);
    },
  });

  const days = useMemo(() => getMonthDays(year, month), [year, month]);
  const events = data?.events || [];

  const eventsByDay = useMemo(() => {
    const map = {};
    events.forEach((e) => {
      const day = parseInt(e.date?.split("-")[2], 10);
      if (!map[day]) map[day] = [];
      map[day].push(e);
    });
    return map;
  }, [events]);

  const prevMonth = () => { if (month === 0) { setMonth(11); setYear(year - 1); } else setMonth(month - 1); };
  const nextMonth = () => { if (month === 11) { setMonth(0); setYear(year + 1); } else setMonth(month + 1); };

  const monthNames = ["Ocak", "\u015eubat", "Mart", "Nisan", "May\u0131s", "Haziran", "Temmuz", "A\u011fustos", "Eyl\u00fcl", "Ekim", "Kas\u0131m", "Aral\u0131k"];
  const dayNames = ["Pzt", "Sal", "\u00c7ar", "Per", "Cum", "Cmt", "Paz"];

  const handleEventClick = (ev) => {
    setDetailModal(ev);
  };

  const handleDayClick = (day) => {
    if (day) {
      setSelectedDay(day);
    }
  };

  const navigateToModule = (type) => {
    const routes = {
      transfer: "/admin/transfers",
      flight: "/admin/flights",
      visa: "/admin/visa",
      insurance: "/admin/insurance",
    };
    if (routes[type]) navigate(routes[type]);
    setSelectedDay(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarDays className="w-7 h-7 text-orange-600" /> Operasyon Takvimi
          </h1>
          <p className="text-gray-500 mt-1">Transfer, u\u00e7u\u015f, vize ve sigorta etkinliklerini tek takvimde g\u00f6r\u00fcn</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
            <option value="">T\u00fcm Etkinlikler</option>
            <option value="transfer">Transferler</option>
            <option value="flight">U\u00e7u\u015flar</option>
            <option value="visa">Vize</option>
            <option value="tour">Turlar</option>
            <option value="insurance">Sigorta</option>
          </select>
        </div>
      </div>

      {detailModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setDetailModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                {(() => { const Icon = EVENT_ICONS[detailModal.type] || CalendarDays; return <Icon className="w-5 h-5" />; })()}
                Etkinlik Detay\u0131
              </h3>
              <button onClick={() => setDetailModal(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium border ${EVENT_COLORS[detailModal.type] || "bg-gray-100"}`}>
                  {EVENT_LABELS[detailModal.type] || detailModal.type}
                </span>
              </div>
              <div>
                <div className="text-sm text-gray-500">Ba\u015fl\u0131k</div>
                <div className="font-medium">{detailModal.title}</div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-sm text-gray-500">Tarih</div>
                  <div className="font-medium">{detailModal.date}</div>
                </div>
                {detailModal.time && (
                  <div>
                    <div className="text-sm text-gray-500">Saat</div>
                    <div className="font-medium">{detailModal.time}</div>
                  </div>
                )}
              </div>
              {detailModal.location && (
                <div>
                  <div className="text-sm text-gray-500">Konum</div>
                  <div className="font-medium">{detailModal.location}</div>
                </div>
              )}
              {detailModal.status && (
                <div>
                  <div className="text-sm text-gray-500">Durum</div>
                  <div className="font-medium">{detailModal.status}</div>
                </div>
              )}
              {detailModal.details && (
                <div>
                  <div className="text-sm text-gray-500">Detay</div>
                  <div className="text-sm text-gray-700">{typeof detailModal.details === "string" ? detailModal.details : JSON.stringify(detailModal.details)}</div>
                </div>
              )}
              <button
                onClick={() => { navigateToModule(detailModal.type); setDetailModal(null); }}
                className="w-full mt-2 bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 text-sm"
              >
                {EVENT_LABELS[detailModal.type] || "Mod\u00fcl"} Sayfas\u0131na Git
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedDay && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelectedDay(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{selectedDay} {monthNames[month]} {year}</h3>
              <button onClick={() => setSelectedDay(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>

            {(eventsByDay[selectedDay] || []).length > 0 && (
              <div className="mb-4 space-y-2">
                <p className="text-sm font-medium text-gray-700">Etkinlikler:</p>
                {eventsByDay[selectedDay].map((ev) => {
                  const Icon = EVENT_ICONS[ev.type] || CalendarDays;
                  return (
                    <button key={ev.id} onClick={() => { setSelectedDay(null); handleEventClick(ev); }}
                      className={`w-full text-left flex items-center gap-2 p-2 rounded-lg border text-sm ${EVENT_COLORS[ev.type] || "bg-gray-100"}`}>
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{ev.time ? `${ev.time} ` : ""}{ev.title}</span>
                    </button>
                  );
                })}
              </div>
            )}

            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">H\u0131zl\u0131 Olu\u015ftur:</p>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => navigateToModule("transfer")} className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700 hover:bg-blue-100">
                  <Bus className="w-4 h-4" /> Transfer
                </button>
                <button onClick={() => navigateToModule("flight")} className="flex items-center gap-2 p-2 bg-sky-50 border border-sky-200 rounded-lg text-sm text-sky-700 hover:bg-sky-100">
                  <Plane className="w-4 h-4" /> U\u00e7u\u015f
                </button>
                <button onClick={() => navigateToModule("visa")} className="flex items-center gap-2 p-2 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-700 hover:bg-purple-100">
                  <FileCheck className="w-4 h-4" /> Vize
                </button>
                <button onClick={() => navigateToModule("insurance")} className="flex items-center gap-2 p-2 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-700 hover:bg-teal-100">
                  <Shield className="w-4 h-4" /> Sigorta
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border shadow-sm">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <button onClick={prevMonth} className="p-2 hover:bg-gray-100 rounded-lg"><ChevronLeft className="w-5 h-5" /></button>
          <h2 className="text-lg font-semibold">{monthNames[month]} {year}</h2>
          <button onClick={nextMonth} className="p-2 hover:bg-gray-100 rounded-lg"><ChevronRight className="w-5 h-5" /></button>
        </div>

        <div className="grid grid-cols-7 border-b">
          {dayNames.map((d) => (
            <div key={d} className="px-2 py-3 text-center text-sm font-medium text-gray-500 border-r last:border-r-0">{d}</div>
          ))}
        </div>

        <div className="grid grid-cols-7">
          {days.map((day, i) => {
            const dayEvents = day ? eventsByDay[day] || [] : [];
            const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            return (
              <div
                key={i}
                onClick={() => handleDayClick(day)}
                className={`min-h-[100px] border-r border-b last:border-r-0 p-1 cursor-pointer hover:bg-blue-50/30 transition ${day ? "bg-white" : "bg-gray-50"}`}
              >
                {day && (
                  <>
                    <div className={`text-sm font-medium px-1 ${isToday ? "bg-blue-600 text-white rounded-full w-7 h-7 flex items-center justify-center" : "text-gray-700"}`}>
                      {day}
                    </div>
                    <div className="space-y-0.5 mt-1">
                      {dayEvents.slice(0, 3).map((ev) => {
                        const Icon = EVENT_ICONS[ev.type] || CalendarDays;
                        return (
                          <div
                            key={ev.id}
                            onClick={(e) => { e.stopPropagation(); handleEventClick(ev); }}
                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs truncate border cursor-pointer hover:opacity-80 ${EVENT_COLORS[ev.type] || "bg-gray-100"}`}
                            title={ev.title}
                          >
                            <Icon className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{ev.time ? `${ev.time} ` : ""}{ev.title?.substring(0, 20)}</span>
                          </div>
                        );
                      })}
                      {dayEvents.length > 3 && <div className="text-xs text-gray-400 px-1">+{dayEvents.length - 3} daha</div>}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {!isLoading && events.length > 0 && (
        <div className="mt-6 flex gap-4 flex-wrap">
          {Object.entries(EVENT_COLORS).map(([type, cls]) => {
            const Icon = EVENT_ICONS[type] || CalendarDays;
            const count = events.filter((e) => e.type === type).length;
            if (count === 0) return null;
            return (
              <div key={type} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm ${cls}`}>
                <Icon className="w-4 h-4" /> {EVENT_LABELS[type] || type}: {count}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
