import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Activity, CheckCircle, Server, Database, GitBranch } from "lucide-react";

export default function Health() {
  const { data: artifacts, isLoading: artifactsLoading, error: artifactsError } = useQuery({
    queryKey: ["artifacts-health"],
    queryFn: () => apiClient.getArtifacts([{ name: "*" }]),
  });

  const { data: tracks, isLoading: tracksLoading, error: tracksError } = useQuery({
    queryKey: ["tracks-health"],
    queryFn: () => apiClient.getTracks(),
  });

  const isHealthy = !artifactsError && !tracksError;
  const isLoading = artifactsLoading || tracksLoading;

  const components = [
    {
      name: "API Server",
      status: isHealthy ? "operational" : "error",
      icon: Server,
      description: "REST API endpoint",
    },
    {
      name: "Artifact Registry",
      status: !artifactsError ? "operational" : "error",
      icon: Database,
      description: `${artifacts?.length ?? 0} artifacts registered`,
    },
    {
      name: "Track System",
      status: !tracksError ? "operational" : "error",
      icon: GitBranch,
      description: tracks?.plannedTracks?.join(", ") || "No tracks",
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "operational":
        return (
          <Badge className="bg-green-500/10 text-green-600 hover:bg-green-500/20">
            Operational
          </Badge>
        );
      case "degraded":
        return (
          <Badge className="bg-yellow-500/10 text-yellow-600 hover:bg-yellow-500/20">
            Degraded
          </Badge>
        );
      case "error":
        return (
          <Badge className="bg-red-500/10 text-red-600 hover:bg-red-500/20">
            Error
          </Badge>
        );
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Health</h1>
        <p className="text-muted-foreground">
          Monitor the status of registry components
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full ${
                  isHealthy
                    ? "bg-green-500/10 text-green-600"
                    : "bg-red-500/10 text-red-600"
                }`}
              >
                {isHealthy ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <Activity className="h-5 w-5" />
                )}
              </div>
              <div>
                <CardTitle>Overall Status</CardTitle>
                <CardDescription>
                  {isLoading
                    ? "Checking..."
                    : isHealthy
                    ? "All systems operational"
                    : "Some systems experiencing issues"}
                </CardDescription>
              </div>
            </div>
            {!isLoading && getStatusBadge(isHealthy ? "operational" : "error")}
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {isLoading
          ? [...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-full" />
                </CardContent>
              </Card>
            ))
          : components.map((component) => (
              <Card key={component.name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <component.icon className="h-4 w-4 text-muted-foreground" />
                      <CardTitle className="text-base">{component.name}</CardTitle>
                    </div>
                    {getStatusBadge(component.status)}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {component.description}
                  </p>
                </CardContent>
              </Card>
            ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Information</CardTitle>
          <CardDescription>Backend service details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium">Base URL</p>
              <p className="mt-1 font-mono text-sm text-muted-foreground">
                http://localhost:8000/api
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-sm font-medium">Authentication</p>
              <p className="mt-1 text-sm text-muted-foreground">
                JWT Token via X-Authorization header
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
