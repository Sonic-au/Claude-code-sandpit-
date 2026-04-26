"use client";

import Link from "next/link";
import { useSavedTrails } from "@/hooks/useSavedTrails";
import type { Trail } from "@/lib/types";
import { GradeBadge, SuitabilityBadges, FeatureTags, SceneryStars } from "@/components/TrailBadges";

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes} minutes`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} hour${h > 1 ? "s" : ""}` : `${h}h ${m}m`;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-stone-800 mb-3 flex items-center gap-2">
        {title}
      </h2>
      {children}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-2.5 border-b border-stone-100 last:border-0">
      <span className="text-sm text-stone-500">{label}</span>
      <span className="text-sm text-stone-800 font-medium text-right max-w-[60%]">{value}</span>
    </div>
  );
}

interface Props {
  trail: Trail;
  allTrails: Trail[];
}

export function TrailDetailClient({ trail, allTrails }: Props) {
  const { isSaved, toggle } = useSavedTrails();
  const saved = isSaved(trail.id);

  const similar = allTrails
    .filter((t) => t.id !== trail.id && (t.trail_type === trail.trail_type || t.grade === trail.grade))
    .slice(0, 3);

  return (
    <div className="min-h-screen bg-stone-50">
      <div className="bg-white border-b border-stone-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <Link href="/" className="text-stone-500 hover:text-stone-800 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 12H5m7-7-7 7 7 7" />
            </svg>
          </Link>
          <span className="text-stone-300">/</span>
          <span className="text-sm text-stone-500 truncate">{trail.name}</span>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <div className="bg-white rounded-2xl border border-stone-200 p-6 md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-stone-900 mb-1">{trail.name}</h1>
              <p className="text-stone-500">{trail.region} · {trail.location}</p>
            </div>
            <button
              onClick={() => toggle(trail.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-medium transition-colors ${
                saved
                  ? "bg-rose-50 border-rose-200 text-rose-600"
                  : "bg-white border-stone-200 text-stone-600 hover:border-stone-300"
              }`}
            >
              <svg className={`w-4 h-4 ${saved ? "fill-rose-500 text-rose-500" : "text-stone-400"}`} fill={saved ? "currentColor" : "none"} stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              {saved ? "Saved" : "Save trail"}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3 mb-5">
            <GradeBadge trail={trail} />
            <span className="text-sm text-stone-500 bg-stone-50 px-3 py-1 rounded-full">{trail.trail_type}</span>
            <span className="text-sm text-stone-500 bg-stone-50 px-3 py-1 rounded-full">{trail.loop_or_one_way}</span>
          </div>

          <p className="text-stone-600 leading-relaxed mb-6">{trail.description}</p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: "Distance", value: `${trail.distance_km} km` },
              { label: "Time", value: formatTime(trail.estimated_time_minutes) },
              { label: "Elevation gain", value: `${trail.elevation_gain_m} m` },
              { label: "Best time", value: trail.best_time },
            ].map((s) => (
              <div key={s.label} className="bg-stone-50 rounded-xl p-3 text-center">
                <div className="text-base font-semibold text-stone-800">{s.value}</div>
                <div className="text-xs text-stone-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-4 mb-6">
            <div className="flex items-center gap-2">
              <span className="text-sm text-stone-500">Scenery</span>
              <SceneryStars rating={trail.scenic_rating} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-stone-500">Accessibility</span>
              <SceneryStars rating={trail.accessibility_rating} />
            </div>
          </div>

          <div className="mb-4">
            <p className="text-xs text-stone-500 mb-2 uppercase tracking-wider font-semibold">Suitability</p>
            <SuitabilityBadges trail={trail} />
          </div>

          <div>
            <p className="text-xs text-stone-500 mb-2 uppercase tracking-wider font-semibold">Features</p>
            <FeatureTags features={trail.features} max={10} />
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl border border-stone-200 p-6">
            <Section title="Trail information">
              <InfoRow label="Start point" value={trail.start_point} />
              <InfoRow label="End point" value={trail.end_point} />
              <InfoRow label="Route type" value={trail.loop_or_one_way} />
              <InfoRow label="Grade" value={trail.grade} />
              <InfoRow label="Parking" value={trail.parking} />
              <InfoRow label="Public transport" value={trail.public_transport} />
            </Section>
          </div>

          <div className="bg-white rounded-2xl border border-stone-200 p-6">
            <Section title="What to bring">
              <ul className="space-y-1.5">
                {trail.what_to_bring.map((item) => (
                  <li key={item} className="flex items-center gap-2 text-sm text-stone-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </Section>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-stone-200 p-6">
          <Section title="Suggested itinerary">
            <p className="text-stone-600 leading-relaxed">{trail.suggested_itinerary}</p>
          </Section>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-emerald-50 rounded-2xl border border-emerald-100 p-6">
            <Section title="Best for">
              <p className="text-stone-700 leading-relaxed">{trail.who_its_best_for}</p>
            </Section>
          </div>

          <div className="bg-amber-50 rounded-2xl border border-amber-100 p-6">
            <Section title="Consider if you are">
              <p className="text-stone-700 leading-relaxed">{trail.who_should_avoid}</p>
            </Section>
          </div>
        </div>

        {trail.safety_notes.length > 0 && (
          <div className="bg-orange-50 rounded-2xl border border-orange-200 p-6">
            <h2 className="text-base font-semibold text-orange-800 mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              Safety notes
            </h2>
            <ul className="space-y-1.5">
              {trail.safety_notes.map((note) => (
                <li key={note} className="flex items-start gap-2 text-sm text-orange-800">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-400 shrink-0 mt-1.5" />
                  {note}
                </li>
              ))}
            </ul>
          </div>
        )}

        {trail.nearby_stops.length > 0 && (
          <div className="bg-white rounded-2xl border border-stone-200 p-6">
            <Section title="Nearby coffee and food">
              <div className="flex flex-wrap gap-2">
                {trail.nearby_stops.map((stop) => (
                  <span key={stop} className="text-sm px-3 py-1.5 bg-stone-50 border border-stone-200 rounded-lg text-stone-700">
                    ☕ {stop}
                  </span>
                ))}
              </div>
            </Section>
          </div>
        )}

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          <strong>Safety disclaimer:</strong> Trail information may change due to weather, fire danger, flooding, maintenance, or access restrictions. Always check official sources before starting a walk.
        </div>

        {similar.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-stone-800 mb-4">Similar trails</h2>
            <div className="grid sm:grid-cols-3 gap-4">
              {similar.map((t) => (
                <Link
                  key={t.id}
                  href={`/trail/${t.id}`}
                  className="bg-white rounded-xl border border-stone-200 p-4 hover:border-emerald-300 hover:shadow-sm transition-all"
                >
                  <p className="font-medium text-stone-800 text-sm mb-1">{t.name}</p>
                  <p className="text-xs text-stone-500 mb-2">{t.region}</p>
                  <div className="flex items-center gap-2 text-xs text-stone-600">
                    <span>{t.distance_km} km</span>
                    <span>·</span>
                    <span>{t.grade}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
