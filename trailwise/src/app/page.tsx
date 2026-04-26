"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import type { Trail, FilterState, SortOption } from "@/lib/types";
import { applyFilters, sortTrails } from "@/lib/scoring";
import { useSavedTrails } from "@/hooks/useSavedTrails";
import { SearchBar } from "@/components/SearchBar";
import { FilterPanel } from "@/components/FilterPanel";
import { ListView } from "@/components/ListView";
import { CompareDrawer } from "@/components/CompareDrawer";
import { SavedTrailsPanel } from "@/components/SavedTrails";
import { RecommendationChat } from "@/components/RecommendationChat";
import allTrailsData from "../../data/trails.json";

const MapView = dynamic(() => import("@/components/MapView").then((m) => ({ default: m.MapView })), { ssr: false });

const ALL_TRAILS = allTrailsData as Trail[];

const DEFAULT_FILTERS: FilterState = {
  location: "",
  maxDistanceKm: null,
  maxTimeMinutes: null,
  grade: [],
  trailType: [],
  features: [],
  dogFriendly: false,
  familyFriendly: false,
  pramFriendly: false,
  wheelchairAccessible: false,
  publicTransport: false,
};

type View = "list" | "map" | "chat" | "saved";

export default function HomePage() {
  const [view, setView] = useState<View>("list");
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [sort, setSort] = useState<SortOption>("recommended");
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const [comparedIds, setComparedIds] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | undefined>();

  const { saved, toggle: toggleSave } = useSavedTrails();

  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => {}
    );
  }, []);

  const filteredTrails = useMemo(() => {
    const filtered = applyFilters(ALL_TRAILS, {
      location: filters.location || undefined,
      maxDistanceKm: filters.maxDistanceKm ?? undefined,
      maxTimeMinutes: filters.maxTimeMinutes ?? undefined,
      grade: filters.grade.length ? filters.grade : undefined,
      trailType: filters.trailType.length ? filters.trailType : undefined,
      features: filters.features.length ? filters.features : undefined,
      dogFriendly: filters.dogFriendly || undefined,
      familyFriendly: filters.familyFriendly || undefined,
      pramFriendly: filters.pramFriendly || undefined,
      wheelchairAccessible: filters.wheelchairAccessible || undefined,
      publicTransport: filters.publicTransport || undefined,
    });
    return sortTrails(filtered, sort, {
      userLocation,
      dogFriendly: filters.dogFriendly,
      familyFriendly: filters.familyFriendly,
    });
  }, [filters, sort, userLocation]);

  const updateFilters = useCallback((partial: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const toggleCompare = useCallback((id: string) => {
    setComparedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  }, []);

  const comparedTrails = useMemo(
    () => ALL_TRAILS.filter((t) => comparedIds.includes(t.id)),
    [comparedIds]
  );

  const activeFiltersCount = [
    filters.location,
    filters.maxDistanceKm,
    filters.maxTimeMinutes,
    ...filters.grade,
    ...filters.trailType,
    ...filters.features,
    filters.dogFriendly && "dog",
    filters.familyFriendly && "family",
    filters.pramFriendly && "pram",
    filters.wheelchairAccessible && "wheelchair",
    filters.publicTransport && "pt",
  ].filter(Boolean).length;

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 shrink-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-2xl">🥾</span>
            <span className="font-bold text-stone-900 text-lg tracking-tight">Trailwise</span>
          </div>

          <div className="flex-1 max-w-xl">
            <SearchBar
              value={filters.location}
              onChange={(v) => updateFilters({ location: v })}
            />
          </div>

          <nav className="flex items-center gap-1 shrink-0">
            {(["list", "map", "chat", "saved"] as View[]).map((v) => {
              const labels: Record<View, string> = {
                list: "List",
                map: "Map",
                chat: "Ask AI",
                saved: saved.length > 0 ? `Saved (${saved.length})` : "Saved",
              };
              return (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    view === v
                      ? "bg-emerald-700 text-white"
                      : "text-stone-600 hover:bg-stone-100"
                  }`}
                >
                  {labels[v]}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — shown in list and map views */}
        {(view === "list" || view === "map") && (
          <div className="hidden md:flex flex-col w-72 shrink-0 border-r border-stone-200 bg-stone-50 overflow-y-auto">
            <div className="p-4">
              <FilterPanel filters={filters} onChange={updateFilters} onReset={resetFilters} />
            </div>
          </div>
        )}

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Mobile filter bar */}
          {(view === "list" || view === "map") && (
            <div className="md:hidden flex items-center gap-2 px-4 py-2 border-b border-stone-200 bg-white shrink-0">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  activeFiltersCount > 0
                    ? "bg-emerald-700 text-white border-emerald-700"
                    : "bg-white border-stone-200 text-stone-600"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                Filters {activeFiltersCount > 0 && `(${activeFiltersCount})`}
              </button>
              <span className="text-sm text-stone-500">{filteredTrails.length} trails</span>
            </div>
          )}

          {/* Mobile filter panel */}
          {showFilters && (view === "list" || view === "map") && (
            <div className="md:hidden p-4 border-b border-stone-200 bg-stone-50 overflow-y-auto max-h-96">
              <FilterPanel filters={filters} onChange={updateFilters} onReset={resetFilters} />
            </div>
          )}

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {view === "list" && (
              <div className="p-4 max-w-5xl mx-auto pb-24">
                <ListView
                  trails={filteredTrails}
                  sort={sort}
                  onSortChange={setSort}
                  savedIds={saved}
                  onToggleSave={toggleSave}
                  comparedIds={comparedIds}
                  onToggleCompare={toggleCompare}
                  highlightedId={highlightedId}
                  onHoverTrail={setHighlightedId}
                  userLocation={userLocation}
                  totalCount={ALL_TRAILS.length}
                />
              </div>
            )}

            {view === "map" && (
              <div className="h-full">
                <MapView
                  trails={filteredTrails}
                  highlightedId={highlightedId}
                  onSelectTrail={setHighlightedId}
                  savedIds={saved}
                  onToggleSave={toggleSave}
                  userLocation={userLocation}
                />
              </div>
            )}

            {view === "chat" && (
              <div className="p-4 max-w-2xl mx-auto flex flex-col" style={{ height: "calc(100vh - 64px)" }}>
                <div className="mb-4 shrink-0">
                  <h1 className="text-xl font-bold text-stone-900">Ask the trail assistant</h1>
                  <p className="text-stone-500 text-sm mt-1">Describe what you are looking for and I will find the right trail.</p>
                </div>
                <div className="flex-1 min-h-0">
                  <RecommendationChat allTrails={ALL_TRAILS} />
                </div>
              </div>
            )}

            {view === "saved" && (
              <div className="p-4 max-w-2xl mx-auto pb-24">
                <SavedTrailsPanel
                  trails={ALL_TRAILS}
                  savedIds={saved}
                  onToggleSave={toggleSave}
                  onClose={() => setView("list")}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Compare drawer */}
      {comparedIds.length > 0 && (
        <CompareDrawer
          trails={comparedTrails}
          onRemove={toggleCompare}
          onClose={() => setComparedIds([])}
        />
      )}
    </div>
  );
}
