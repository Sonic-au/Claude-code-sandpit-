"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import type { Trail } from "@/lib/types";
import { applyFilters, sortTrails } from "@/lib/scoring";
import { GradeBadge } from "./TrailBadges";

interface Message {
  role: "user" | "assistant";
  text: string;
  trails?: Trail[];
}

function parseRequest(input: string, allTrails: Trail[]): { trails: Trail[]; explanation: string } {
  const lower = input.toLowerCase();

  const filters: Parameters<typeof applyFilters>[1] = {};
  const reasons: string[] = [];

  if (lower.includes("dog") || lower.includes("pet")) {
    filters.dogFriendly = true;
    reasons.push("dog-friendly");
  }
  if (lower.includes("family") || lower.includes("kids") || lower.includes("children")) {
    filters.familyFriendly = true;
    reasons.push("family-friendly");
  }
  if (lower.includes("pram") || lower.includes("stroller") || lower.includes("buggy")) {
    filters.pramFriendly = true;
    reasons.push("pram-friendly");
  }
  if (lower.includes("wheelchair") || lower.includes("accessible")) {
    filters.wheelchairAccessible = true;
    reasons.push("wheelchair accessible");
  }

  const easyMatch = lower.includes("easy") || lower.includes("flat") || lower.includes("gentle") || lower.includes("casual");
  const hardMatch = lower.includes("hard") || lower.includes("challenging") || lower.includes("strenuous") || lower.includes("difficult");
  const modMatch = lower.includes("moderate") || lower.includes("medium");
  if (easyMatch && !hardMatch) {
    filters.grade = ["Easy", "Easy to Moderate"];
    reasons.push("easy grade");
  } else if (hardMatch && !easyMatch) {
    filters.grade = ["Hard", "Moderate to Hard"];
    reasons.push("challenging grade");
  } else if (modMatch) {
    filters.grade = ["Moderate", "Easy to Moderate", "Moderate to Hard"];
    reasons.push("moderate grade");
  }

  const timeMatch = lower.match(/(\d+)\s*hour/);
  if (timeMatch) {
    filters.maxTimeMinutes = parseInt(timeMatch[1]) * 60;
    reasons.push(`under ${timeMatch[1]} hour${parseInt(timeMatch[1]) > 1 ? "s" : ""}`);
  } else if (lower.includes("quick") || lower.includes("short")) {
    filters.maxTimeMinutes = 90;
    reasons.push("under 1.5 hours");
  } else if (lower.includes("half day") || lower.includes("half-day")) {
    filters.maxTimeMinutes = 240;
    reasons.push("half-day");
  }

  const featureMap: Record<string, string[]> = {
    "coastal": ["Coastal", "Headland & Coastal", "Coastal & Cliff Top"],
    "coast": ["Coastal", "Headland & Coastal", "Coastal & Cliff Top"],
    "beach": ["Coastal", "Headland & Coastal"],
    "waterfall": ["Waterfall & Valley", "Canyon & Rainforest"],
    "bush": ["Harbour & Bush", "Riverside & Bush", "Bushland & Waterside"],
    "harbour": ["Harbour & Bush"],
    "canyon": ["Canyon & Rainforest"],
    "rainforest": ["Canyon & Rainforest"],
    "lake": ["Lakeside & Bush"],
    "river": ["Riverside & Bush"],
    "cliff": ["Coastal & Cliff Top"],
  };

  for (const [keyword, types] of Object.entries(featureMap)) {
    if (lower.includes(keyword)) {
      filters.trailType = types;
      reasons.push(`${keyword} trail`);
      break;
    }
  }

  const featureKeywords: Record<string, string> = {
    "cafe": "Cafes",
    "coffee": "Cafes",
    "swim": "Swimming",
    "scenic": "Ocean views",
    "views": "Ocean views",
    "wildlife": "Birdlife",
    "lighthouse": "Lighthouse",
  };

  const wantedFeatures: string[] = [];
  for (const [kw, feature] of Object.entries(featureKeywords)) {
    if (lower.includes(kw)) wantedFeatures.push(feature);
  }
  if (wantedFeatures.length > 0) {
    filters.features = wantedFeatures;
    reasons.push(`featuring ${wantedFeatures.join(", ").toLowerCase()}`);
  }

  const locationKeywords = ["sydney", "blue mountains", "manly", "bondi", "northern beaches", "parramatta", "western sydney", "eastern suburbs", "north shore"];
  for (const loc of locationKeywords) {
    if (lower.includes(loc)) {
      filters.location = loc;
      reasons.push(`near ${loc}`);
      break;
    }
  }

  const matched = applyFilters(allTrails, filters);
  const sorted = sortTrails(matched, "recommended", { dogFriendly: filters.dogFriendly, familyFriendly: filters.familyFriendly });
  const top = sorted.slice(0, 3);

  const explanation = top.length === 0
    ? "I couldn't find trails matching all those criteria. Try relaxing some filters."
    : `Here are ${top.length} trail${top.length > 1 ? "s" : ""} I'd recommend${reasons.length > 0 ? " — " + reasons.join(", ") : ""}:`;

  return { trails: top, explanation };
}

const SUGGESTIONS = [
  "Easy coastal walk under 2 hours near Sydney",
  "Dog-friendly bush walk",
  "Scenic walk with coffee nearby",
  "Family waterfall walk",
  "Challenging Blue Mountains walk",
  "Short walk with great views",
];

interface Props {
  allTrails: Trail[];
  onApplyFilters?: (trailIds: string[]) => void;
}

export function RecommendationChat({ allTrails, onApplyFilters }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hi! Tell me the kind of walk you're after today — location, time available, fitness level, features — and I'll find the right trail for you.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend(text?: string) {
    const query = text ?? input.trim();
    if (!query) return;
    setInput("");
    setLoading(true);

    const userMsg: Message = { role: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);

    setTimeout(() => {
      const { trails, explanation } = parseRequest(query, allTrails);
      const assistantMsg: Message = { role: "assistant", text: explanation, trails };
      setMessages((prev) => [...prev, assistantMsg]);
      setLoading(false);
    }, 400);
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-stone-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-stone-100">
        <h3 className="font-semibold text-stone-800">Trail assistant</h3>
        <p className="text-xs text-stone-500 mt-0.5">Describe the walk you want today</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] ${msg.role === "user" ? "bg-emerald-700 text-white" : "bg-stone-100 text-stone-800"} rounded-2xl px-4 py-3 text-sm`}>
              <p className="leading-relaxed">{msg.text}</p>
              {msg.trails && msg.trails.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.trails.map((trail) => (
                    <div key={trail.id} className="bg-white rounded-xl p-3 shadow-sm">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <p className="font-semibold text-stone-900 text-sm leading-tight">{trail.name}</p>
                        <GradeBadge trail={trail} />
                      </div>
                      <p className="text-xs text-stone-500 mb-2">{trail.region} · {trail.distance_km} km · {Math.round(trail.estimated_time_minutes / 60 * 10) / 10}h</p>
                      <Link
                        href={`/trail/${trail.id}`}
                        className="text-xs font-semibold text-emerald-700 hover:text-emerald-900"
                      >
                        View guide →
                      </Link>
                    </div>
                  ))}
                </div>
              )}
              {msg.trails && msg.trails.length === 0 && msg.role === "assistant" && (
                <p className="mt-2 text-xs text-stone-500">Try a more general query, like "easy coastal walk".</p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-stone-100 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-stone-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length === 1 && (
        <div className="px-4 pb-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleSend(s)}
              className="text-xs px-3 py-1.5 bg-stone-50 border border-stone-200 rounded-full text-stone-600 hover:border-emerald-300 hover:text-emerald-700 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="px-4 py-3 border-t border-stone-100">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe the walk you want…"
            className="flex-1 px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-40 text-white rounded-xl transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
