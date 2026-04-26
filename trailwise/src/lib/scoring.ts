import type { Trail, ScoreOptions } from "./types";

const GRADE_ORDER: Record<string, number> = {
  "Easy": 1,
  "Easy to Moderate": 2,
  "Moderate": 3,
  "Moderate to Hard": 4,
  "Hard": 5,
};

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function scoreTrail(trail: Trail, opts: ScoreOptions): number {
  let score = 50;

  if (opts.userLocation) {
    const dist = haversineKm(
      opts.userLocation.lat,
      opts.userLocation.lng,
      trail.latitude,
      trail.longitude
    );
    score += Math.max(0, 20 - dist * 0.5);
  }

  if (opts.maxTimeMinutes && trail.estimated_time_minutes <= opts.maxTimeMinutes) {
    const margin = opts.maxTimeMinutes - trail.estimated_time_minutes;
    score += Math.min(15, margin / 10);
  } else if (opts.maxTimeMinutes && trail.estimated_time_minutes > opts.maxTimeMinutes) {
    score -= 20;
  }

  if (opts.maxDistanceKm && trail.distance_km <= opts.maxDistanceKm) {
    score += 10;
  } else if (opts.maxDistanceKm && trail.distance_km > opts.maxDistanceKm) {
    score -= 15;
  }

  if (opts.preferredFeatures && opts.preferredFeatures.length > 0) {
    const matches = trail.features.filter((f) =>
      opts.preferredFeatures!.some((pf) =>
        f.toLowerCase().includes(pf.toLowerCase())
      )
    ).length;
    score += matches * 5;
  }

  if (opts.dogFriendly && trail.dog_friendly) score += 20;
  if (opts.dogFriendly && !trail.dog_friendly) score -= 30;

  if (opts.familyFriendly && trail.family_friendly) score += 10;

  score += trail.scenic_rating * 2;
  score += trail.accessibility_rating;

  return score;
}

export function sortTrails(
  trails: Trail[],
  sort: string,
  opts: ScoreOptions = {}
): Trail[] {
  const sorted = [...trails];
  switch (sort) {
    case "recommended":
      return sorted.sort((a, b) => scoreTrail(b, opts) - scoreTrail(a, opts));
    case "nearest":
      if (!opts.userLocation) return sorted;
      return sorted.sort((a, b) => {
        const da = haversineKm(opts.userLocation!.lat, opts.userLocation!.lng, a.latitude, a.longitude);
        const db = haversineKm(opts.userLocation!.lat, opts.userLocation!.lng, b.latitude, b.longitude);
        return da - db;
      });
    case "shortest":
      return sorted.sort((a, b) => a.distance_km - b.distance_km);
    case "longest":
      return sorted.sort((a, b) => b.distance_km - a.distance_km);
    case "easiest":
      return sorted.sort((a, b) => (GRADE_ORDER[a.grade] ?? 3) - (GRADE_ORDER[b.grade] ?? 3));
    case "most_scenic":
      return sorted.sort((a, b) => b.scenic_rating - a.scenic_rating);
    case "best_families":
      return sorted.sort((a, b) => (b.family_friendly ? 1 : 0) - (a.family_friendly ? 1 : 0));
    case "best_dogs":
      return sorted.sort((a, b) => (b.dog_friendly ? 1 : 0) - (a.dog_friendly ? 1 : 0));
    case "time_asc":
      return sorted.sort((a, b) => a.estimated_time_minutes - b.estimated_time_minutes);
    case "time_desc":
      return sorted.sort((a, b) => b.estimated_time_minutes - a.estimated_time_minutes);
    default:
      return sorted;
  }
}

export function applyFilters(trails: Trail[], filters: {
  location?: string;
  maxDistanceKm?: number | null;
  maxTimeMinutes?: number | null;
  grade?: string[];
  trailType?: string[];
  features?: string[];
  dogFriendly?: boolean;
  familyFriendly?: boolean;
  pramFriendly?: boolean;
  wheelchairAccessible?: boolean;
  publicTransport?: boolean;
}): Trail[] {
  return trails.filter((trail) => {
    if (filters.location) {
      const loc = filters.location.toLowerCase();
      if (
        !trail.location.toLowerCase().includes(loc) &&
        !trail.region.toLowerCase().includes(loc) &&
        !trail.name.toLowerCase().includes(loc) &&
        !trail.tags.some((t) => t.includes(loc))
      ) return false;
    }
    if (filters.maxTimeMinutes && trail.estimated_time_minutes > filters.maxTimeMinutes) return false;
    if (filters.maxDistanceKm && trail.distance_km > filters.maxDistanceKm) return false;
    if (filters.grade && filters.grade.length > 0 && !filters.grade.includes(trail.grade)) return false;
    if (filters.trailType && filters.trailType.length > 0 && !filters.trailType.includes(trail.trail_type)) return false;
    if (filters.features && filters.features.length > 0) {
      const hasAll = filters.features.every((f) =>
        trail.features.some((tf) => tf.toLowerCase().includes(f.toLowerCase()))
      );
      if (!hasAll) return false;
    }
    if (filters.dogFriendly && !trail.dog_friendly) return false;
    if (filters.familyFriendly && !trail.family_friendly) return false;
    if (filters.pramFriendly && !trail.pram_friendly) return false;
    if (filters.wheelchairAccessible && !trail.wheelchair_accessible) return false;
    if (filters.publicTransport && trail.public_transport === "None") return false;
    return true;
  });
}

export function distanceFromUser(trail: Trail, userLocation?: { lat: number; lng: number }): number | null {
  if (!userLocation) return null;
  return Math.round(haversineKm(userLocation.lat, userLocation.lng, trail.latitude, trail.longitude));
}
