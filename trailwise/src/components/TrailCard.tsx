"use client";

import Link from "next/link";
import type { Trail } from "@/lib/types";
import { GradeBadge, SuitabilityBadges, FeatureTags, SceneryStars } from "./TrailBadges";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

interface Props {
  trail: Trail;
  isSaved: boolean;
  onToggleSave: (id: string) => void;
  isCompared: boolean;
  onToggleCompare: (id: string) => void;
  distanceKm?: number | null;
  isHighlighted?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export function TrailCard({
  trail,
  isSaved,
  onToggleSave,
  isCompared,
  onToggleCompare,
  distanceKm,
  isHighlighted,
  onMouseEnter,
  onMouseLeave,
}: Props) {
  return (
    <div
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={`group bg-white rounded-2xl border transition-all duration-200 overflow-hidden ${
        isHighlighted
          ? "border-emerald-500 shadow-lg shadow-emerald-100"
          : "border-stone-200 hover:border-stone-300 hover:shadow-md"
      }`}
    >
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-stone-900 text-base leading-tight truncate">
              {trail.name}
            </h3>
            <p className="text-stone-500 text-sm mt-0.5 truncate">
              {trail.region} · {trail.location}
            </p>
          </div>
          <button
            onClick={() => onToggleSave(trail.id)}
            aria-label={isSaved ? "Remove from saved" : "Save trail"}
            className="shrink-0 p-1.5 rounded-full hover:bg-stone-100 transition-colors"
          >
            <svg
              className={`w-5 h-5 transition-colors ${isSaved ? "text-rose-500 fill-rose-500" : "text-stone-400"}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </button>
        </div>

        <div className="flex items-center gap-3 mb-3">
          <GradeBadge trail={trail} />
          <span className="text-xs text-stone-500 bg-stone-50 px-2 py-0.5 rounded-full">{trail.trail_type}</span>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3 text-center">
          <div className="bg-stone-50 rounded-lg py-2 px-1">
            <div className="text-sm font-semibold text-stone-800">{trail.distance_km} km</div>
            <div className="text-xs text-stone-500">Distance</div>
          </div>
          <div className="bg-stone-50 rounded-lg py-2 px-1">
            <div className="text-sm font-semibold text-stone-800">{formatTime(trail.estimated_time_minutes)}</div>
            <div className="text-xs text-stone-500">Time</div>
          </div>
          <div className="bg-stone-50 rounded-lg py-2 px-1">
            <div className="text-sm font-semibold text-stone-800">{trail.elevation_gain_m}m</div>
            <div className="text-xs text-stone-500">Elevation</div>
          </div>
        </div>

        <div className="mb-3">
          <div className="flex items-center gap-1 mb-1">
            <span className="text-xs text-stone-500">Scenery</span>
            <SceneryStars rating={trail.scenic_rating} />
          </div>
          <FeatureTags features={trail.features} max={3} />
        </div>

        <div className="mb-4">
          <SuitabilityBadges trail={trail} compact />
        </div>

        {distanceKm != null && (
          <p className="text-xs text-stone-500 mb-3">~{distanceKm} km from you</p>
        )}

        <div className="flex gap-2 items-center">
          <Link
            href={`/trail/${trail.id}`}
            className="flex-1 text-center bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-medium py-2 px-4 rounded-xl transition-colors"
          >
            View guide
          </Link>
          <button
            onClick={() => onToggleCompare(trail.id)}
            className={`px-3 py-2 rounded-xl text-sm font-medium border transition-colors ${
              isCompared
                ? "bg-sky-50 border-sky-300 text-sky-700"
                : "bg-white border-stone-200 text-stone-600 hover:border-stone-300"
            }`}
          >
            {isCompared ? "✓ Compare" : "Compare"}
          </button>
        </div>
      </div>
    </div>
  );
}
