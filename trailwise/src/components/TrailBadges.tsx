import type { Trail } from "@/lib/types";

const GRADE_COLOUR: Record<string, string> = {
  "Easy": "bg-emerald-100 text-emerald-800",
  "Easy to Moderate": "bg-lime-100 text-lime-800",
  "Moderate": "bg-amber-100 text-amber-800",
  "Moderate to Hard": "bg-orange-100 text-orange-800",
  "Hard": "bg-red-100 text-red-800",
};

interface Props {
  trail: Trail;
  compact?: boolean;
}

export function GradeBadge({ trail }: { trail: Trail }) {
  const colour = GRADE_COLOUR[trail.grade] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${colour}`}>
      {trail.grade}
    </span>
  );
}

export function SuitabilityBadges({ trail, compact = false }: Props) {
  const badges: { label: string; show: boolean; colour: string }[] = [
    { label: "Dog friendly", show: trail.dog_friendly, colour: "bg-amber-50 text-amber-700 border border-amber-200" },
    { label: "Family", show: trail.family_friendly, colour: "bg-blue-50 text-blue-700 border border-blue-200" },
    { label: "Pram", show: trail.pram_friendly, colour: "bg-purple-50 text-purple-700 border border-purple-200" },
    { label: "Wheelchair", show: trail.wheelchair_accessible, colour: "bg-teal-50 text-teal-700 border border-teal-200" },
    { label: "PT access", show: trail.public_transport !== "None", colour: "bg-indigo-50 text-indigo-700 border border-indigo-200" },
  ];

  return (
    <div className="flex flex-wrap gap-1">
      {badges.filter((b) => b.show).map((b) => (
        <span key={b.label} className={`inline-block px-2 py-0.5 rounded-full text-xs ${b.colour}`}>
          {compact ? b.label.split(" ")[0] : b.label}
        </span>
      ))}
    </div>
  );
}

export function FeatureTags({ features, max = 3 }: { features: string[]; max?: number }) {
  return (
    <div className="flex flex-wrap gap-1">
      {features.slice(0, max).map((f) => (
        <span key={f} className="inline-block px-2 py-0.5 bg-stone-100 text-stone-600 rounded text-xs">
          {f}
        </span>
      ))}
      {features.length > max && (
        <span className="inline-block px-2 py-0.5 bg-stone-100 text-stone-400 rounded text-xs">
          +{features.length - max}
        </span>
      )}
    </div>
  );
}

export function SceneryStars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <svg key={i} className={`w-3 h-3 ${i <= rating ? "text-amber-400" : "text-gray-200"}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}
