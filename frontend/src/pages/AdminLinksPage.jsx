import React, { useEffect, useState } from "react";
import { Link2, AlertCircle, Loader2 } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { formatDateTime } from "../utils/formatters";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";

// Hook: Load all 3 endpoints + create Maps
function useAdminLinksData() {
  const [links, setLinks] = useState([]);
  const [agencies, setAgencies] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [linksResp, agenciesResp, hotelsResp] = await Promise.all([
        api.get("/admin/agency-hotel-links/"),
        api.get("/admin/agencies/"),
        api.get("/admin/hotels/"),
      ]);

      console.log("[AdminLinks] Loaded data:", {
        links: linksResp.data?.length || 0,
        agencies: agenciesResp.data?.length || 0,
        hotels: hotelsResp.data?.length || 0,
      });

      setLinks(linksResp.data || []);
      setAgencies(agenciesResp.data || []);
      setHotels(hotelsResp.data || []);
    } catch (err) {
      console.error("[AdminLinks] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return { links, agencies, hotels, loading, error, reload: loadAll };
}

// Enrich links with names (frontend join)
function enrichLinks(links, agencies, hotels) {
  // Create Maps for O(1) lookup
  const agencyById = new Map(agencies.map((a) => [a.id, a]));
  const hotelById = new Map(hotels.map((h) => [h.id, h]));

  return links.map((link) => {
    const agency = agencyById.get(link.agency_id);
    const hotel = hotelById.get(link.hotel_id);

    // Fallback logging
    if (!agency) {
      console.warn(`[AdminLinks] Missing agency for id: ${link.agency_id}`);
    }
    if (!hotel) {
      console.warn(`[AdminLinks] Missing hotel for id: ${link.hotel_id}`);
    }

    return {
      ...link,
      agency_name: agency?.name || "Bilinmiyor",
      hotel_name: hotel?.name || "Bilinmiyor",
      hotel_city: hotel?.city || "",
      hotel_country: hotel?.country || "",
    };
  });
}

export default function AdminLinksPage() {
  const { links, agencies, hotels, loading, error, reload } = useAdminLinksData();
  const [toggleLoading, setToggleLoading] = useState(null);

  useEffect(() => {
    reload();
  }, []);

  async function toggleLinkActive(linkId, currentActive) {
    setToggleLoading(linkId);
    try {
      await api.patch(`/admin/agency-hotel-links/${linkId}`, {
        active: !currentActive,
      });
      console.log(`[AdminLinks] Toggle success: ${linkId} → ${!currentActive}`);
      toast.success("Link durumu güncellendi");
      // Refresh after successful PATCH
      await reload();
    } catch (err) {
      console.error(`[AdminLinks] Toggle error:`, err);
      toast.error(apiErrorMessage(err));
    } finally {
      setToggleLoading(null);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bağlantı Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta-otel bağlantıları
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Linkler yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bağlantı Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta-otel bağlantıları
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Linkler yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={reload}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  // Enrich + sort
  const enriched = enrichLinks(links, agencies, hotels).sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  // Empty state
  if (enriched.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bağlantı Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta-otel bağlantıları
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Link2 className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz acenta-otel linki yok
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Bu sürümde doğrudan link oluşturma devre dışı. Acenta-otel bağlantıları operasyon ekibi tarafından yönetilmektedir.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Data table
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Bağlantı Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {enriched.length} acenta-otel bağlantısı
          </p>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Acenta</TableHead>
              <TableHead className="font-semibold">Otel</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold">Oluşturma</TableHead>
              <TableHead className="font-semibold text-xs">Oluşturan</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {enriched.map((link) => (
              <TableRow key={link.id}>
                <TableCell className="font-medium">{link.agency_name}</TableCell>
                <TableCell>
                  <div>
                    <div className="font-medium">{link.hotel_name}</div>
                    {(link.hotel_city || link.hotel_country) && (
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {link.hotel_city}
                        {link.hotel_city && link.hotel_country && " • "}
                        {link.hotel_country}
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={link.active}
                      onCheckedChange={() => toggleLinkActive(link.id, link.active)}
                      disabled={loading || toggleLoading === link.id}
                    />
                    <span className="text-sm text-muted-foreground">
                      {toggleLoading === link.id ? (
                        <Loader2 className="h-4 w-4 animate-spin inline" />
                      ) : link.active ? (
                        "Aktif"
                      ) : (
                        "Pasif"
                      )}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDateTime(link.created_at)}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {link.created_by || "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
