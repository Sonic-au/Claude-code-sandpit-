"use client";

import { useState, useEffect } from "react";

const KEY = "trailwise_saved";

export function useSavedTrails() {
  const [saved, setSaved] = useState<string[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setSaved(JSON.parse(raw));
    } catch {}
  }, []);

  function toggle(id: string) {
    setSaved((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });
  }

  function isSaved(id: string) {
    return saved.includes(id);
  }

  return { saved, toggle, isSaved };
}
