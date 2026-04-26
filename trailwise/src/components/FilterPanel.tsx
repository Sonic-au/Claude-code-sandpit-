"use client";

import type { FilterState } from "@/lib/types";

const GRADES = ["Easy", "Easy to Moderate", "Moderate", "Moderate to Hard", "Hard"];
const TRAIL_TYPES = ["Coastal", "Harbour & Bush", "Riverside & Bush", "Canyon & Rainforest", "Waterfall & Valley", "Headland & Coastal", "Coastal & Rock Platform", "Bushland & Waterside", "Lakeside & Bush", "Coastal & Cliff Top"];
const FEATURES = ["Ocean views", "Beaches", "Waterfalls", "Rainforest", "Bushland", "River views", "Lake views", "Harbour views", "Cafes", "Birdlife", "Swimming", "Lighthouse"];
const TIME_OPTIONS = [
  { label: "Under 1 hour", value: 60 },
  { label: "Under 2 hours", value: 120 },
  { label: "Under 3 hours", value: 180 },
  { label: "Half day (4h)", value: 240 },
  { label: "Full day", value: 480 },
];
const DIST_OPTIONS = [
  { label: "Under 3 km", value: 3 },
  { label: "Under 5 km", value: 5 },
  { label: "Under 8 km", value: 8 },
  { label: "Under 12 km", value: 12 },
];

interface Props {
  filters: FilterState;
  onChange: (f: Partial<FilterState>) => void;
  onReset: () => void;
}

function CheckboxGroup({
  options,
  selected,
  onChange,
}: {
  options: string[];
  selected: string[];
  onChange: (v: string[]) => void;
}) {
  function toggle(opt: string) {
    onChange(selected.includes(opt) ? selected.filter((x) => x !== opt) : [...selected, opt]);
  }
  return (
    <div className="flex flex-col gap-1">
      {options.map((opt) => (
        <label key={opt} className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={selected.includes(opt)}
            onChange={() => toggle(opt)}
            className="w-4 h-4 rounded border-stone-300 text-emerald-600 focus:ring-emerald-500"
          />
          <span className="text-sm text-stone-700 group-hover:text-stone-900">{opt}</span>
        </label>
      ))}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">{title}</h4>
      {children}
    </div>
  );
}

export function FilterPanel({ filters, onChange, onReset }: Props) {
  const hasFilters =
    filters.location ||
    filters.maxTimeMinutes ||
    filters.maxDistanceKm ||
    filters.grade.length ||
    filters.trailType.length ||
    filters.features.length ||
    filters.dogFriendly ||
    filters.familyFriendly ||
    filters.pramFriendly ||
    filters.wheelchairAccessible ||
    filters.publicTransport;

  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-stone-800">Filters</h3>
        {hasFilters && (
          <button onClick={onReset} className="text-xs text-emerald-600 hover:text-emerald-800 font-medium">
            Reset all
          </button>
        )}
      </div>

      <Section title="Max time">
        <div className="flex flex-col gap-1">
          {TIME_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="radio"
                name="maxTime"
                checked={filters.maxTimeMinutes === opt.value}
                onChange={() => onChange({ maxTimeMinutes: filters.maxTimeMinutes === opt.value ? null : opt.value })}
                className="w-4 h-4 border-stone-300 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-sm text-stone-700 group-hover:text-stone-900">{opt.label}</span>
            </label>
          ))}
        </div>
      </Section>

      <Section title="Max trail length">
        <div className="flex flex-col gap-1">
          {DIST_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="radio"
                name="maxDist"
                checked={filters.maxDistanceKm === opt.value}
                onChange={() => onChange({ maxDistanceKm: filters.maxDistanceKm === opt.value ? null : opt.value })}
                className="w-4 h-4 border-stone-300 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-sm text-stone-700 group-hover:text-stone-900">{opt.label}</span>
            </label>
          ))}
        </div>
      </Section>

      <Section title="Grade">
        <CheckboxGroup
          options={GRADES}
          selected={filters.grade}
          onChange={(v) => onChange({ grade: v })}
        />
      </Section>

      <Section title="Trail type">
        <CheckboxGroup
          options={TRAIL_TYPES}
          selected={filters.trailType}
          onChange={(v) => onChange({ trailType: v })}
        />
      </Section>

      <Section title="Features">
        <CheckboxGroup
          options={FEATURES}
          selected={filters.features}
          onChange={(v) => onChange({ features: v })}
        />
      </Section>

      <Section title="Suitability">
        {[
          { key: "dogFriendly", label: "Dog friendly" },
          { key: "familyFriendly", label: "Family friendly" },
          { key: "pramFriendly", label: "Pram friendly" },
          { key: "wheelchairAccessible", label: "Wheelchair accessible" },
          { key: "publicTransport", label: "Public transport" },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer group mb-1">
            <input
              type="checkbox"
              checked={filters[key as keyof FilterState] as boolean}
              onChange={(e) => onChange({ [key]: e.target.checked })}
              className="w-4 h-4 rounded border-stone-300 text-emerald-600 focus:ring-emerald-500"
            />
            <span className="text-sm text-stone-700 group-hover:text-stone-900">{label}</span>
          </label>
        ))}
      </Section>
    </div>
  );
}
