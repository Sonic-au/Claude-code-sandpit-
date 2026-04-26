export interface Trail {
  id: string;
  name: string;
  location: string;
  region: string;
  distance_km: number;
  estimated_time_minutes: number;
  grade: string;
  trail_type: string;
  features: string[];
  dog_friendly: boolean;
  family_friendly: boolean;
  pram_friendly: boolean;
  wheelchair_accessible: boolean;
  best_time: string;
  start_point: string;
  end_point: string;
  loop_or_one_way: string;
  elevation_gain_m: number;
  public_transport: string;
  parking: string;
  safety_notes: string[];
  nearby_stops: string[];
  latitude: number;
  longitude: number;
  description: string;
  what_to_bring: string[];
  suggested_itinerary: string;
  who_its_best_for: string;
  who_should_avoid: string;
  scenic_rating: number;
  accessibility_rating: number;
  weather_suitability: string[];
  tags: string[];
}

export type Grade = "Easy" | "Easy to Moderate" | "Moderate" | "Moderate to Hard" | "Hard";

export type SortOption =
  | "recommended"
  | "nearest"
  | "shortest"
  | "longest"
  | "easiest"
  | "most_scenic"
  | "best_families"
  | "best_dogs"
  | "time_asc"
  | "time_desc";

export interface FilterState {
  location: string;
  maxDistanceKm: number | null;
  maxTimeMinutes: number | null;
  grade: string[];
  trailType: string[];
  features: string[];
  dogFriendly: boolean;
  familyFriendly: boolean;
  pramFriendly: boolean;
  wheelchairAccessible: boolean;
  publicTransport: boolean;
}

export interface ScoreOptions {
  userLocation?: { lat: number; lng: number };
  maxTimeMinutes?: number;
  maxDistanceKm?: number;
  preferredFeatures?: string[];
  dogFriendly?: boolean;
  familyFriendly?: boolean;
}
