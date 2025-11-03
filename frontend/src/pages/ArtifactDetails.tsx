import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Calendar, TrendingUp, Download, Edit, Trash2, Brain, Database, FileCode
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";

import { DefaultService } from "@/api/generated/services/DefaultService";
import { OpenAPI } from "@/api/generated/client";

type FlatArtifact = {
  id: string;
  name: string;
  type: "model" | "dataset" | "code" | string;
  created_at?: string;
  description?: string;
  version?: string;
  net_score?: number;
  url?: string | null;
};

const getTypeIcon = (type: string) => {
  switch (type) {
    case "model": return <Brain className="h-6 w-6" />;
    case "dataset": return <Database className="h-6 w-6" />;
    case "code": return <FileCode className="h-6 w-6" />;
    default: return null;
  }
};

async function fetchArtifactEnvelope(artifactType: string, artifactId: string) {
  const svc = DefaultService as any;

  // Prefer known codegen names
  if (typeof svc.artifactsGet === "function") {
    return svc.artifactsGet(artifactType, Number(artifactId));
  }
  if (typeof svc.artifactsArtifactTypeArtifactIdGet === "function") {
    return svc.artifactsArtifactTypeArtifactIdGet(artifactType, Number(artifactId));
  }
  if (typeof svc.artifactGet === "function") {
    try {
      return await svc.artifactGet(artifactId);
    } catch {
      // ignore and fallback to fetch
    }
  }

  // Spec fallback
  const res = await fetch(`${OpenAPI.BASE ?? ""}/artifacts/${artifactType}/${artifactId}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`GET failed: ${res.status}`);
  return res.json();
}

function normalizeEnvelopeToFlat(envelope: any): FlatArtifact {
  const md = envelope?.metadata ?? {};
  const data = envelope?.data ?? {};
  return {
    id: String(md.id ?? ""),
    name: String(md.name ?? ""),
    type: String(md.type ?? "model"),
    created_at: envelope?.created_at ?? undefined,
    description: envelope?.description ?? undefined,
    version: envelope?.version ?? undefined,
    net_score: envelope?.net_score ?? undefined,
    url: data?.url ?? null,
  };
}

export default function ArtifactDetails() {
  // Must be routed as /artifacts/:type/:id
  const { type, id } = useParams<{ type: string; id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftUrl, setDraftUrl] = useState("");

  const { data: artifact, isLoading, isError } = useQuery<FlatArtifact>({
    queryKey: ["artifact", type, id],
    enabled: Boolean(type && id),
    queryFn: async () => normalizeEnvelopeToFlat(await fetchArtifactEnvelope(type!, id!)),
  });

  // DELETE (spec): DELETE /artifacts/{artifact_type}/{id}
  const deleteMutation = useMutation({
    mutationFn: async () => {
      const svc = DefaultService as any;
      if (typeof svc.artifactsDelete === "function") {
        return svc.artifactsDelete(type!, Number(id));
      }
      if (typeof svc.artifactsArtifactTypeArtifactIdDelete === "function") {
        return svc.artifactsArtifactTypeArtifactIdDelete(type!, Number(id));
      }
      const res = await fetch(`${OpenAPI.BASE ?? ""}/artifacts/${type}/${id}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(`DELETE failed: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["browse"] });
      qc.invalidateQueries({ queryKey: ["search"] });
      navigate("/");
    },
  });

  const handleDelete = () => {
    if (!type || !id) return;
    const ok = window.confirm("Delete this artifact? This action cannot be undone.");
    if (ok) deleteMutation.mutate();
  };

  // DOWNLOAD (off-spec): GET /artifacts/{type}/{id}/download
  // Let the browser handle redirect/attachment; no need to fetch blob in JS.
  function startDownload(artifactType: string, artifactId: string, subset: "full" | "weights" | "runtime" = "full") {
  const base = OpenAPI.BASE || "http://10.186.15.115:8000"; // ensure this is set at build time
  const qs = subset === "full" ? "" : `?subset=${subset}`;
  const href = `${base}/artifacts/${artifactType}/${artifactId}/download${qs}`;

  const a = document.createElement("a");
  a.href = href;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// usage
const handleDownload = () => {
  if (!type || !id) return;
  startDownload(type, id, "weights"); // or "weights"
};



  // EDIT (spec): PUT /artifacts/{artifact_type}/{id}
  const editMutation = useMutation({
    mutationFn: async (payload: { name: string; url?: string }) => {
      const body = {
        metadata: { id, type, name: payload.name },
        data: { url: payload.url ?? null },
      };
      const svc = DefaultService as any;
      if (typeof svc.artifactsPut === "function") {
        return svc.artifactsPut(type!, Number(id), body);
      }
      if (typeof svc.artifactsArtifactTypeArtifactIdPut === "function") {
        return svc.artifactsArtifactTypeArtifactIdPut(type!, Number(id), body);
      }
      const res = await fetch(`${OpenAPI.BASE ?? ""}/artifacts/${type}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`PUT failed: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      setIsEditing(false);
      qc.invalidateQueries({ queryKey: ["artifact", type, id] });
      qc.invalidateQueries({ queryKey: ["browse"] });
      qc.invalidateQueries({ queryKey: ["search"] });
    },
  });

  const openEdit = () => {
    if (!artifact) return;
    setDraftName(artifact.name ?? "");
    setDraftUrl(artifact.url ?? "");
    setIsEditing(true);
  };
  const saveEdit = () => {
    const name = draftName.trim();
    const url = draftUrl.trim();
    if (!name) return alert("Name is required.");
    editMutation.mutate({ name, url: url || undefined });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen py-8 px-4">
        <div className="max-w-5xl mx-auto space-y-6">
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (isError || !artifact) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Artifact Not Found</h1>
          <p className="text-muted-foreground mb-6">
            The artifact you're looking for doesn't exist.
          </p>
          <Button onClick={() => navigate("/")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Artifacts
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-6">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Artifacts
        </Button>

        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-secondary text-secondary-foreground">
                  {getTypeIcon(artifact.type)}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-3xl">{artifact.name}</CardTitle>
                    <Badge variant="secondary" className="capitalize">
                      {artifact.type}
                    </Badge>
                  </div>
                  <CardDescription className="text-base">
                    {artifact.description ?? "No description provided."}
                  </CardDescription>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-6 text-sm">
              {artifact.created_at && (
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Uploaded:</span>
                  <span className="font-medium">
                    {new Date(artifact.created_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              {typeof artifact.net_score === "number" && (
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Net Score:</span>
                  <span className="font-medium">{artifact.net_score.toFixed(2)}</span>
                </div>
              )}
              {artifact.version && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Version:</span>
                  <span className="font-medium">v{artifact.version}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>About This Artifact</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="font-semibold mb-2">Description</h3>
                  <p className="text-muted-foreground">
                    {artifact.description ?? "—"}
                  </p>
                </div>
                <Separator />
                <div>
                  <h3 className="font-semibold mb-2">Technical Details</h3>
                  <p className="text-muted-foreground">
                    Additional technical information and specifications will be displayed here once
                    integrated with the backend API.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metrics & Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {typeof artifact.net_score === "number" && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Net Score</span>
                      <span className="text-2xl font-bold">
                        {artifact.net_score.toFixed(2)}
                      </span>
                    </div>
                  )}
                  <Separator />
                  <p className="text-sm text-muted-foreground">
                    Additional performance metrics and evaluation results will be available when
                    connected to the backend API.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full" onClick={handleDownload}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>

                <Button
                  variant="outline"
                  className="w-full"
                  onClick={openEdit}
                  disabled={!artifact}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  Edit Details
                </Button>

                <Button
                  variant="destructive"
                  className="w-full"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {deleteMutation.isPending ? "Deleting..." : "Delete"}
                </Button>

                <p className="text-xs text-muted-foreground pt-2">
                  Download uses a helper endpoint (HF snapshot/zip or redirect). Edit/ Delete use spec endpoints.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Artifact ID</span>
                  <p className="font-mono mt-1">{artifact.id}</p>
                </div>
                <Separator />
                <div>
                  <span className="text-muted-foreground">Type</span>
                  <p className="capitalize mt-1">{artifact.type}</p>
                </div>
                <Separator />
                {artifact.created_at && (
                  <div>
                    <span className="text-muted-foreground">Upload Date</span>
                    <p className="mt-1">{new Date(artifact.created_at).toLocaleString()}</p>
                  </div>
                )}
                {artifact.version && (
                  <>
                    <Separator />
                    <div>
                      <span className="text-muted-foreground">Version</span>
                      <p className="mt-1">v{artifact.version}</p>
                    </div>
                  </>
                )}
                {artifact.url && (
                  <>
                    <Separator />
                    <div>
                      <span className="text-muted-foreground">Source URL</span>
                      <p className="mt-1 break-all">{artifact.url}</p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Edit dialog */}
      <Dialog open={isEditing} onOpenChange={setIsEditing}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Artifact Details</DialogTitle>
            <DialogDescription>
              Update the artifact name (required) and optional source URL. This calls the spec PUT endpoint.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="name">Name<span className="text-destructive">*</span></Label>
              <Input
                id="name"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                placeholder="artifact-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">Source URL (optional)</Label>
              <Input
                id="url"
                value={draftUrl}
                onChange={(e) => setDraftUrl(e.target.value)}
                placeholder="https://huggingface.co/owner/repo or https://..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditing(false)} disabled={editMutation.isPending}>
              Cancel
            </Button>
            <Button onClick={saveEdit} disabled={editMutation.isPending}>
              {editMutation.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
