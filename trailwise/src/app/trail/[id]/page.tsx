import trails from "../../../../data/trails.json";
import type { Trail } from "@/lib/types";
import { TrailDetailClient } from "./TrailDetailClient";
import { notFound } from "next/navigation";

export function generateStaticParams() {
  return (trails as Trail[]).map((t) => ({ id: t.id }));
}

export default async function TrailDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const trail = (trails as Trail[]).find((t) => t.id === id);
  if (!trail) notFound();
  return <TrailDetailClient trail={trail} allTrails={trails as Trail[]} />;
}
