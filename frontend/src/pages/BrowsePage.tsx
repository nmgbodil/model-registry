// src/pages/BrowsePage.tsx
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import ArtifactCard from "@/components/ArtifactCard";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, ChevronRight, Database } from "lucide-react";

/** ---- Config ---- */
const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";
const AUTH_TOKEN =
  (import.meta.env.VITE_API_TOKEN as string | undefined) ?? "dev-token";

/** ---- Types that match your UI expectations ---- */
type ArtifactType = "model" | "dataset" | "code";
type UIArtifact = {
  id: string;
  name: string;
  type: ArtifactType;
  version?: string;
  description?: string;
  created_at?: string;
  net_score?: number;
};

type ListResult = {
  items: UIArtifact[];
  nextOffset: number;
};

/** ---- Spec-compliant list call ----
 * POST /artifacts?offset=<number>
 * body: [{ name: "*", types?: ["model"|"dataset"|"code"] }]
 * headers: X-Authorization: <token>
 * response: 200 JSON array of { name,id,type }
 * response header: offset: <nextOffset>
 */
async function listArtifactsSpec(params: {
  offset: number;
  limit: number;
  artifactType: string; // "all" | ArtifactType
}): Promise<ListResult> {
  const { offset, limit, artifactType } = params;

  // Build ArtifactQuery[]
  const body: Array<{ name: string; types?: ArtifactType[] }> = [
    artifactType === "all"
      ? { name: "*" }
      : { name: "*", types: [artifactType as ArtifactType] },
  ];

  // Note: limit is not in spec as a query param. We simulate page-size by
  // server-side offset + returning up to your server’s configured page size.
  // If your backend supports a non-spec "limit", remove it here to stay strict.
  const url = new URL(`${API_BASE}/artifacts`);
  url.searchParams.set("offset", String(offset));

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Authorization": AUTH_TOKEN,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`ArtifactsList failed: ${res.status} ${res.statusText} ${text}`);
  }

  const nextOffsetHeader = res.headers.get("offset");
  const nextOffset = nextOffsetHeader ? Number(nextOffsetHeader) : offset;

  const meta = (await res.json()) as Array<{
    name: string;
    id: string;
    type: ArtifactType;
  }>;

  // Map to UI shape; optional fields left undefined (spec only returns metadata).
  const items: UIArtifact[] = meta.map((m) => ({
    id: String(m.id),
    name: m.name,
    type: m.type,
    version: undefined,
    description: undefined,
    created_at: undefined,
    net_score: undefined,
  }));

  // If you want client-side page size control, slice here:
  const sliced = items.slice(0, limit);
  const computedNext = offset + sliced.length;

  return { items: sliced, nextOffset: computedNext };
}

export default function BrowsePage() {
  const [artifactType, setArtifactType] = useState<string>("all");
  const [pageSize, setPageSize] = useState<number>(10);
  const [offset, setOffset] = useState<number>(0);
  const [offsetHistory, setOffsetHistory] = useState<number[]>([]);

  const queryKey = useMemo(
    () => ["artifacts", artifactType, offset, pageSize] as const,
    [artifactType, offset, pageSize]
  );

  const { data, isLoading, isError, error } = useQuery<ListResult>({
    queryKey,
    queryFn: () =>
      listArtifactsSpec({
        offset,
        limit: pageSize,
        artifactType,
      }),
    staleTime: 10_000,
  });

  const handleNext = () => {
    if (data && data.items.length >= pageSize) {
      setOffsetHistory((h) => [...h, offset]);
      setOffset(data.nextOffset);
    }
  };

  const handlePrevious = () => {
    setOffsetHistory((h) => {
      if (h.length === 0) return h;
      const newHistory = [...h];
      const prevOffset = newHistory.pop()!;
      setOffset(prevOffset);
      return newHistory;
    });
  };

  const handleTypeChange = (value: string) => {
    setArtifactType(value);
    setOffset(0);
    setOffsetHistory([]);
  };

  const handlePageSizeChange = (value: string) => {
    setPageSize(parseInt(value, 10));
    setOffset(0);
    setOffsetHistory([]);
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Browse Artifacts</h1>
        <p className="text-muted-foreground">
          Explore all artifacts in the registry with pagination
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1">
          <Select value={artifactType} onValueChange={handleTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="model">Models</SelectItem>
              <SelectItem value="dataset">Datasets</SelectItem>
              <SelectItem value="code">Code</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-full sm:w-32">
          <Select value={String(pageSize)} onValueChange={handlePageSizeChange}>
            <SelectTrigger>
              <SelectValue placeholder="Page size" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10 per page</SelectItem>
              <SelectItem value="25">25 per page</SelectItem>
              <SelectItem value="50">50 per page</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isError && (
        <div className="bg-destructive/10 border border-destructive rounded-lg p-4 mb-6">
          <p className="text-destructive font-medium">Error loading artifacts</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : "Failed to fetch artifacts. Please try again."}
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: pageSize }).map((_, i) => (
            <div key={i} className="border rounded-lg p-4 space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {data.items.map((artifact) => (
              <ArtifactCard key={artifact.id} artifact={artifact} />
            ))}
          </div>

          <div className="flex items-center justify-between border-t pt-4">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={offsetHistory.length === 0}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Showing {offset + 1} - {offset + data.items.length}
            </span>
            <Button
              variant="outline"
              onClick={handleNext}
              disabled={data.items.length < pageSize}
            >
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </>
      ) : (
        <div className="text-center py-12 border rounded-lg bg-muted/20">
          <Database className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">No artifacts found</h3>
          <p className="text-muted-foreground mb-4">
            There are no artifacts matching your filters yet.
          </p>
          <Button variant="outline" onClick={() => (window.location.href = "/upload")}>
            Upload your first artifact
          </Button>
        </div>
      )}
    </div>
  );
}
