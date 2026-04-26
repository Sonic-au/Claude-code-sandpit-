"use client";

import { useEffect, useRef } from "react";
import type { Trail } from "@/lib/types";

interface Props {
  trails: Trail[];
  highlightedId?: string | null;
  onSelectTrail?: (id: string) => void;
  savedIds?: string[];
  onToggleSave?: (id: string) => void;
  userLocation?: { lat: number; lng: number };
}

const GRADE_COLOUR: Record<string, string> = {
  "Easy": "#16a34a",
  "Easy to Moderate": "#65a30d",
  "Moderate": "#d97706",
  "Moderate to Hard": "#ea580c",
  "Hard": "#dc2626",
};

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function MapView({ trails, highlightedId, onSelectTrail, savedIds = [], onToggleSave, userLocation }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);
  const markersRef = useRef<Map<string, import("leaflet").Marker>>(new Map());

  useEffect(() => {
    if (typeof window === "undefined" || !containerRef.current) return;
    if (mapRef.current) return;

    import("leaflet").then((L) => {
      // Fix default icon paths
      // @ts-expect-error – Leaflet private
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      const map = L.map(containerRef.current!, {
        center: [-33.8688, 151.2093],
        zoom: 10,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = map;

      if (userLocation) {
        L.circleMarker([userLocation.lat, userLocation.lng], {
          radius: 8,
          fillColor: "#3b82f6",
          color: "#fff",
          weight: 2,
          fillOpacity: 1,
        }).addTo(map).bindPopup("You are here");
      }
    });

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      markersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;
    import("leaflet").then((L) => {
      const map = mapRef.current!;
      const existing = new Set(markersRef.current.keys());

      trails.forEach((trail) => {
        existing.delete(trail.id);
        const colour = GRADE_COLOUR[trail.grade] ?? "#6b7280";
        const isHighlighted = trail.id === highlightedId;
        const isSaved = savedIds.includes(trail.id);

        const icon = L.divIcon({
          className: "",
          html: `
            <div style="
              background:${colour};
              border:${isHighlighted ? "3px solid #0f172a" : "2px solid #fff"};
              border-radius:50%;
              width:${isHighlighted ? "20px" : "16px"};
              height:${isHighlighted ? "20px" : "16px"};
              box-shadow:0 2px 6px rgba(0,0,0,0.25);
              cursor:pointer;
              transition:all 0.15s;
              ${isSaved ? "outline:2px solid #f43f5e;outline-offset:2px;" : ""}
            "></div>`,
          iconSize: [isHighlighted ? 20 : 16, isHighlighted ? 20 : 16],
          iconAnchor: [isHighlighted ? 10 : 8, isHighlighted ? 10 : 8],
        });

        if (markersRef.current.has(trail.id)) {
          markersRef.current.get(trail.id)!.setIcon(icon);
        } else {
          const marker = L.marker([trail.latitude, trail.longitude], { icon })
            .addTo(map)
            .bindPopup(`
              <div style="min-width:180px;font-family:system-ui,sans-serif">
                <div style="font-weight:700;font-size:14px;margin-bottom:4px;color:#1c1917">${trail.name}</div>
                <div style="font-size:12px;color:#78716c;margin-bottom:6px">${trail.region} · ${trail.trail_type}</div>
                <div style="display:flex;gap:8px;font-size:12px;margin-bottom:8px">
                  <span><strong>${trail.distance_km} km</strong></span>
                  <span><strong>${formatTime(trail.estimated_time_minutes)}</strong></span>
                </div>
                <div style="display:inline-block;background:${colour}22;color:${colour};border-radius:999px;padding:2px 8px;font-size:11px;font-weight:600;margin-bottom:8px">${trail.grade}</div>
                <div style="display:flex;gap:6px;margin-top:6px">
                  <a href="/trail/${trail.id}" style="flex:1;text-align:center;background:#15803d;color:#fff;text-decoration:none;padding:5px 10px;border-radius:8px;font-size:12px;font-weight:600">View guide</a>
                </div>
              </div>
            `, { maxWidth: 220 });

          marker.on("click", () => onSelectTrail?.(trail.id));
          markersRef.current.set(trail.id, marker);
        }
      });

      existing.forEach((id) => {
        markersRef.current.get(id)?.remove();
        markersRef.current.delete(id);
      });
    });
  }, [trails, highlightedId, savedIds]);

  useEffect(() => {
    if (!mapRef.current || !highlightedId) return;
    const trail = trails.find((t) => t.id === highlightedId);
    if (!trail) return;
    import("leaflet").then(() => {
      mapRef.current?.panTo([trail.latitude, trail.longitude], { animate: true });
    });
  }, [highlightedId, trails]);

  return (
    <>
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      />
      <div ref={containerRef} className="w-full h-full rounded-2xl overflow-hidden" />
    </>
  );
}
