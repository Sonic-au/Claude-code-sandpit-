"use client";

import type { Trail, FilterState, SortOption } from "@/lib/types";
import { TrailCard } from "./TrailCard";
import { distanceFromUser } from "@/lib/scoring";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "recommended", label: "Recommended" },
  { value: "nearest", label: "Nearest" },
  { value: "shortest", label: "Shortest walk" },
  { value: "longest", label: "Longest walk" },
  { value: "easiest", label: "Easiest" },
  { value: "most_scenic", label: "Most scenic" },
  { value: "best_families", label: "Best for families" },
  { value: "best_dogs", label: "Best for dogs" },
  { value: "time_asc", label: "Shortest time" },
  { value: "time_desc", label: "Longest time" },
];

interface Props {
  trails: Trail[];
  sort: SortOption;
  onSortChange: (s: SortOption) => void;
  savedIds: string[];
  onToggleSave: (id: string) => void;
  comparedIds: string[];
  onToggleCompare: (id: string) => void;
  highlightedId?: string | null;
  onHoverTrail?: (id: string | null) => void;
  userLocation?: { lat: number; lng: number };
  totalCount: number;
}

export function ListView({
  trails,
  sort,
  onSortChange,
  savedIds,
  onToggleSave,
  comparedIds,
  onToggleCompare,
  highlightedId,
  onHoverTrail,
  userLocation,
  totalCount,
}: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-stone-500">
          {trails.length === totalCount
            ? `${totalCount} trail${totalCount !== 1 ? "s" : ""}`
            : `${trails.length} of ${totalCount} trails`}
        </p>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="text-sm border border-stone-200 rounded-lg px-3 py-1.5 bg-white text-stone-700 focus:outline-none focus:border-emerald-500"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {trails.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">🥾</div>
          <p className="text-stone-600 font-medium">No trails match your filters</p>
          <p className="text-stone-400 text-sm mt-1">Try adjusting or resetting your filters</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-1 xl:grid-cols-2">
          {trails.map((trail) => (
            <TrailCard
              key={trail.id}
              trail={trail}
              isSaved={savedIds.includes(trail.id)}
              onToggleSave={onToggleSave}
              isCompared={comparedIds.includes(trail.id)}
              onToggleCompare={onToggleCompare}
              distanceKm={distanceFromUser(trail, userLocation)}
              isHighlighted={highlightedId === trail.id}
              onMouseEnter={() => onHoverTrail?.(trail.id)}
              onMouseLeave={() => onHoverTrail?.(null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
