import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Brain, Activity, GitBranch, Shield, Database, Code } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArtifactType } from "@/lib/api";

const typeIcons: Record<ArtifactType, React.ElementType> = {
  model: Brain,
  dataset: Database,
  code: Code,
};

export default function Dashboard() {
  const { data: artifacts, isLoading: artifactsLoading } = useQuery({
    queryKey: ["artifacts"],
    queryFn: () => apiClient.getArtifacts([{ name: "*" }]),
  });

  const { data: tracks, isLoading: tracksLoading } = useQuery({
    queryKey: ["tracks"],
    queryFn: () => apiClient.getTracks(),
  });

  const stats = [
    {
      title: "Total Artifacts",
      value: artifacts?.length ?? 0,
      icon: Brain,
      description: "Registered models, datasets & code",
    },
    {
      title: "Active Track",
      value: tracks?.plannedTracks?.[0] ?? "N/A",
      icon: GitBranch,
      description: "Current implementation track",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to the Trustworthy Model Registry
        </p>
      </div>

      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">System Statistics</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              </CardHeader>
              <CardContent>
                {artifactsLoading || tracksLoading ? (
                  <div role="status" aria-label={`Loading ${stat.title}`}>
                    <Skeleton className="h-8 w-20" />
                    <span className="sr-only">Loading...</span>
                  </div>
                ) : (
                  <>
                    <div className="text-2xl font-bold">{stat.value}</div>
                    <p className="text-xs text-muted-foreground">{stat.description}</p>
                  </>
                )}
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge 
                  variant="default" 
                  className="bg-green-500/10 text-green-700 hover:bg-green-500/20"
                >
                  Operational
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">All systems running</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Security</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Protected</div>
              <p className="text-xs text-muted-foreground">Authentication enabled</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and operations</CardDescription>
          </CardHeader>
          <CardContent>
            <nav aria-label="Quick actions" className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link to="/artifacts">Browse Artifacts</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/artifacts/new">Upload Artifact</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/health">View Health</Link>
              </Button>
            </nav>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle id="recent-artifacts-title">Recent Artifacts</CardTitle>
            <CardDescription id="recent-artifacts-desc">Latest registered models, datasets & code</CardDescription>
          </CardHeader>
          <CardContent>
            {artifactsLoading ? (
              <div 
                className="space-y-2" 
                role="status" 
                aria-label="Loading recent artifacts"
              >
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <span className="sr-only">Loading recent artifacts...</span>
              </div>
            ) : artifacts && artifacts.length > 0 ? (
              <nav 
                aria-labelledby="recent-artifacts-title"
                aria-describedby="recent-artifacts-desc"
                className="space-y-2"
              >
                {artifacts.slice(0, 5).map((artifact) => {
                  const TypeIcon = typeIcons[artifact.type] || Brain;
                  return (
                    <Link
                      key={artifact.id}
                      to={`/artifacts/${artifact.type}/${artifact.id}`}
                      className="flex items-center justify-between rounded-md border p-2 hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      aria-label={`View ${artifact.name} (${artifact.type})`}
                    >
                      <div className="flex items-center gap-2">
                        <TypeIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                        <span className="font-medium">{artifact.name}</span>
                      </div>
                      <Badge variant="secondary">{artifact.type}</Badge>
                    </Link>
                  );
                })}
              </nav>
            ) : (
              <p className="text-sm text-muted-foreground" role="status">No artifacts found</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
