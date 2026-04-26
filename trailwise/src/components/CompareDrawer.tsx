"use client";

import Link from "next/link";
import type { Trail } from "@/lib/types";
import { GradeBadge } from "./TrailBadges";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

function Check({ val }: { val: boolean }) {
  return val ? (
    <span className="text-emerald-600 font-semibold">✓</span>
  ) : (
    <span className="text-stone-300">—</span>
  );
}

function Stars({ n }: { n: number }) {
  return (
    <div className="flex gap-0.5 justify-center">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className={`w-2 h-2 rounded-full ${i <= n ? "bg-amber-400" : "bg-stone-200"}`} />
      ))}
    </div>
  );
}

interface Props {
  trails: Trail[];
  onRemove: (id: string) => void;
  onClose: () => void;
}

type CompareRow = {
  label: string;
  render: (t: Trail) => React.ReactNode;
};

const ROWS: CompareRow[] = [
  { label: "Distance", render: (t) => `${t.distance_km} km` },
  { label: "Time", render: (t) => formatTime(t.estimated_time_minutes) },
  { label: "Grade", render: (t) => <GradeBadge trail={t} /> },
  { label: "Elevation gain", render: (t) => `${t.elevation_gain_m} m` },
  { label: "Scenic rating", render: (t) => <Stars n={t.scenic_rating} /> },
  { label: "Accessibility", render: (t) => <Stars n={t.accessibility_rating} /> },
  { label: "Dog friendly", render: (t) => <Check val={t.dog_friendly} /> },
  { label: "Family friendly", render: (t) => <Check val={t.family_friendly} /> },
  { label: "Pram friendly", render: (t) => <Check val={t.pram_friendly} /> },
  { label: "Wheelchair", render: (t) => <Check val={t.wheelchair_accessible} /> },
  { label: "Public transport", render: (t) => <span className="text-xs text-stone-600">{t.public_transport}</span> },
  { label: "Route type", render: (t) => t.loop_or_one_way },
];

export function CompareDrawer({ trails, onRemove, onClose }: Props) {
  if (trails.length === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-stone-200 shadow-2xl">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between py-3 border-b border-stone-100">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-stone-800 text-sm">Compare trails</span>
            <span className="text-xs text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full">{trails.length} selected</span>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-700 text-sm">
            Close ✕
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left py-3 pr-4 font-medium text-stone-500 text-xs w-32">Metric</th>
                {trails.map((t) => (
                  <th key={t.id} className="py-3 px-3 text-center min-w-[160px]">
                    <div className="flex flex-col items-center gap-1">
                      <span className="font-semibold text-stone-800 text-sm leading-tight">{t.name}</span>
                      <span className="text-xs text-stone-400">{t.region}</span>
                      <div className="flex gap-2 mt-1">
                        <Link href={`/trail/${t.id}`} className="text-xs text-emerald-700 font-semibold hover:underline">
                          View guide
                        </Link>
                        <button onClick={() => onRemove(t.id)} className="text-xs text-stone-400 hover:text-red-500">
                          Remove
                        </button>
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label} className="border-t border-stone-50">
                  <td className="py-2 pr-4 text-xs text-stone-500 font-medium">{row.label}</td>
                  {trails.map((t) => (
                    <td key={t.id} className="py-2 px-3 text-center text-stone-700">
                      {row.render(t)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
