"use client";

import { useParams } from "next/navigation";

import { FullLiveProgress } from "@/features/simulation/full-live-progress";

export default function FullLiveJobPage() {
  const params = useParams<{ jobId: string }>();
  return <FullLiveProgress jobId={params.jobId} />;
}
