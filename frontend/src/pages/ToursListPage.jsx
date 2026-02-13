import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Search, MapPin, Clock, Users, ChevronRight, Filter, X, Globe, Calendar,
} from "lucide-react";

const HERO_IMAGE = "https://images.unsplash.com/photo-1525849306000-cc26ceb5c1d7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwzfHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=1600";

const DEFAULT_IMAGES = [
  "https://images.unsplash.com/photo-1683669446872-f956fe268beb?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODF8MHwxfHNlYXJjaHwxfHx0b3VyJTIwbGFuZHNjYXBlfGVufDB8fHx8MTc3MTAwNTY2OXww&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1554366347-897a5113f6ab?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHw0fHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1584467541268-b040f83be3fd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwyfHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1614088459293-5669fadc3448?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwxfHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=600",
  "https://images.unsplash.com/photo-1643892150764-75ee9a645f6e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODF8MHwxfHNlYXJjaHwzfHx0b3VyJTIwbGFuZHNjYXBlfGVufDB8fHx8MTc3MTAwNTY2OXww&ixlib=rb-4.1.0&q=85&w=600",
];

function getDefaultImage(index) {
  return DEFAULT_IMAGES[index % DEFAULT_IMAGES.length];
}

function formatPrice(price, currency) {
  if (!price) return "Fiyat bilgisi yok";
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: currency || "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

export default function ToursListPage() {
  const navigate = useNavigate();
  const [tours, setTours] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedDestination, setSelectedDestination] = useState("");
  const [categories, setCategories] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const loadTours = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = { page, page_size: 12 };
      if (search) params.q = search;
      if (selectedCategory) params.category = selectedCategory;
      if (selectedDestination) params.destination = selectedDestination;
      const res = await api.get("/tours", { params });
      setTours(res.data?.items || []);
      setTotal(res.data?.total || 0);
      if (res.data?.filters) {
        setCategories(res.data.filters.categories || []);
        setDestinations(res.data.filters.destinations || []);
      }
    } catch (e) {
      setError("Turlar yuklenirken hata olustu.");
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedCategory, selectedDestination]);

  useEffect(() => {
    loadTours();
  }, [loadTours]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadTours();
  };

  const clearFilters = () => {
    setSearch("");
    setSelectedCategory("");
    setSelectedDestination("");
    setPage(1);
  };

  const totalPages = Math.ceil(total / 12);
  const hasActiveFilters = search || selectedCategory || selectedDestination;

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative h-64 md:h-80 overflow-hidden rounded-xl mb-8">
        <img
          src={HERO_IMAGE}
          alt="Turlar"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Turlarimiz
          </h1>
          <p className="text-white/80 text-sm md:text-base max-w-2xl">
            En guzel destinasyonlara unutulmaz tur deneyimleri. Hayalinizdeki tatili kesfetmek icin turlari inceleyin.
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Tur adi, bolge veya aciklama ile ara..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button type="submit" size="sm">
              <Search className="h-4 w-4 mr-1" />
              Ara
            </Button>
          </form>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={showFilters ? "bg-primary/10" : ""}
          >
            <Filter className="h-4 w-4 mr-1" />
            Filtrele
            {hasActiveFilters && (
              <Badge variant="secondary" className="ml-2 h-5 w-5 p-0 flex items-center justify-center text-xs">
                !
              </Badge>
            )}
          </Button>
        </div>

        {showFilters && (
          <Card className="p-4">
            <div className="flex flex-wrap gap-4 items-end">
              {categories.length > 0 && (
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Kategori</label>
                  <select
                    className="w-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedCategory}
                    onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
                  >
                    <option value="">Tumunu Goster</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              )}
              {destinations.length > 0 && (
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Destinasyon</label>
                  <select
                    className="w-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedDestination}
                    onChange={(e) => { setSelectedDestination(e.target.value); setPage(1); }}
                  >
                    <option value="">Tumunu Goster</option>
                    {destinations.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              )}
              {hasActiveFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="h-4 w-4 mr-1" />
                  Filtreleri Temizle
                </Button>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Results info */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          {total > 0 ? `${total} tur bulundu` : ""}
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="overflow-hidden animate-pulse">
              <div className="h-48 bg-muted" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-1/2" />
                <div className="h-3 bg-muted rounded w-1/3" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <Card className="p-8 text-center">
          <p className="text-red-500 mb-3">{error}</p>
          <Button variant="outline" size="sm" onClick={loadTours}>
            Tekrar Dene
          </Button>
        </Card>
      )}

      {/* No results */}
      {!loading && !error && tours.length === 0 && (
        <Card className="p-12 text-center">
          <Globe className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">Henuz tur bulunamadi</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {hasActiveFilters
              ? "Arama kriterlerinize uygun tur bulunamadi. Filtreleri degistirmeyi deneyin."
              : "Admin panelinden yeni tur ekleyebilirsiniz."}
          </p>
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={clearFilters}>
              Filtreleri Temizle
            </Button>
          )}
        </Card>
      )}

      {/* Tour Cards */}
      {!loading && !error && tours.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {tours.map((tour, idx) => {
            const coverImg = tour.cover_image || getDefaultImage(idx);
            const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
            const imgSrc = coverImg.startsWith("/api/") ? `${backendUrl}${coverImg}` : coverImg;

            return (
              <Card
                key={tour.id}
                className="group overflow-hidden cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
                onClick={() => navigate(`/app/tours/${tour.id}`)}
              >
                {/* Image */}
                <div className="relative h-48 overflow-hidden">
                  <img
                    src={imgSrc}
                    alt={tour.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    onError={(e) => { e.target.src = getDefaultImage(idx); }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                  {tour.category && (
                    <Badge className="absolute top-3 left-3 bg-white/90 text-foreground hover:bg-white text-xs">
                      {tour.category}
                    </Badge>
                  )}
                  <div className="absolute bottom-3 right-3">
                    <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-bold shadow">
                      {formatPrice(tour.base_price, tour.currency)}
                    </span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4">
                  <h3 className="font-semibold text-base mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                    {tour.name}
                  </h3>

                  {tour.description && (
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {tour.description}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                    {tour.destination && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {tour.destination}
                      </span>
                    )}
                    {tour.duration_days > 0 && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {tour.duration_days} Gun
                      </span>
                    )}
                    {tour.max_participants > 0 && (
                      <span className="flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        Maks. {tour.max_participants}
                      </span>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-primary hover:text-primary"
                    >
                      Detaylari Gor
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Onceki
          </Button>
          <span className="flex items-center px-3 text-sm text-muted-foreground">
            Sayfa {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Sonraki
          </Button>
        </div>
      )}
    </div>
  );
}
