"use client";

import Link from "next/link";
import type { Trail } from "@/lib/types";
import { GradeBadge } from "./TrailBadges";

interface Props {
  trails: Trail[];
  savedIds: string[];
  onToggleSave: (id: string) => void;
  onClose: () => void;
}

function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function SavedTrailsPanel({ trails, savedIds, onToggleSave, onClose }: Props) {
  const saved = trails.filter((t) => savedIds.includes(t.id));

  return (
    <div className="bg-white rounded-2xl border border-stone-200 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-stone-100">
        <div>
          <h3 className="font-semibold text-stone-800">Saved trails</h3>
          <p className="text-xs text-stone-500 mt-0.5">{saved.length} trail{saved.length !== 1 ? "s" : ""} saved</p>
        </div>
        <button onClick={onClose} className="text-stone-400 hover:text-stone-600">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {saved.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <p className="text-3xl mb-2">🏔️</p>
          <p className="text-stone-500 text-sm">No saved trails yet.</p>
          <p className="text-stone-400 text-xs mt-1">Tap the heart icon on any trail to save it.</p>
        </div>
      ) : (
        <div className="divide-y divide-stone-100">
          {saved.map((trail) => (
            <div key={trail.id} className="flex items-center gap-3 px-5 py-3 hover:bg-stone-50 transition-colors">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-stone-800 text-sm truncate">{trail.name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <GradeBadge trail={trail} />
                  <span className="text-xs text-stone-400">{trail.distance_km} km · {formatTime(trail.estimated_time_minutes)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Link
                  href={`/trail/${trail.id}`}
                  className="text-xs text-emerald-700 font-semibold hover:text-emerald-900"
                >
                  View
                </Link>
                <button
                  onClick={() => onToggleSave(trail.id)}
                  className="text-rose-400 hover:text-rose-600 transition-colors"
                  aria-label="Remove from saved"
                >
                  <svg className="w-4 h-4 fill-rose-400" viewBox="0 0 24 24">
                    <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
