import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient, ArtifactType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Package, Search, Plus, ExternalLink, Brain, Database, Code } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { announce } from "@/lib/a11y";

const typeIcons: Record<ArtifactType, React.ElementType> = {
  model: Brain,
  dataset: Database,
  code: Code,
};

const typeColors: Record<ArtifactType, string> = {
  model: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  dataset: "bg-green-500/10 text-green-700 border-green-500/20",
  code: "bg-purple-500/10 text-purple-700 border-purple-500/20",
};

export default function Artifacts() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isRegex, setIsRegex] = useState(false);
  const { toast } = useToast();

  const { data: artifacts, isLoading, error, refetch } = useQuery({
    queryKey: ["artifacts", searchQuery, isRegex],
    queryFn: async () => {
      if (searchQuery && isRegex) {
        return apiClient.searchArtifactsByRegex(searchQuery);
      }
      if (searchQuery) {
        return apiClient.getArtifacts([{ name: searchQuery }]);
      }
      return apiClient.getArtifacts([{ name: "*" }]);
    },
  });

  // Announce search results to screen readers
  useEffect(() => {
    if (!isLoading && artifacts) {
      announce(`Found ${artifacts.length} artifacts`);
    }
  }, [artifacts, isLoading]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    refetch();
  };

  if (error) {
    toast({
      variant: "destructive",
      title: "Error loading artifacts",
      description: error instanceof Error ? error.message : "Failed to fetch artifacts",
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Artifacts</h1>
          <p className="text-muted-foreground">
            Browse and manage registered models, datasets, and code
          </p>
        </div>
        <Button asChild>
          <Link to="/artifacts/new">
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Upload Artifact
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle id="search-title">Search Artifacts</CardTitle>
          <CardDescription id="search-description">Search by name or regex pattern</CardDescription>
        </CardHeader>
        <CardContent>
          <form 
            onSubmit={handleSearch} 
            className="flex gap-2"
            role="search"
            aria-labelledby="search-title"
            aria-describedby="search-description"
          >
            <div className="relative flex-1">
              <Search 
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" 
                aria-hidden="true"
              />
              <Input
                placeholder="Search artifacts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                aria-label="Search artifacts by name or pattern"
              />
            </div>
            <Button
              type="button"
              variant={isRegex ? "default" : "outline"}
              onClick={() => setIsRegex(!isRegex)}
              aria-pressed={isRegex}
              aria-label={isRegex ? "Regex mode enabled" : "Enable regex mode"}
            >
              Regex
            </Button>
            <Button type="submit">Search</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle id="artifact-list-title">Artifact List</CardTitle>
          <CardDescription 
            id="artifact-count"
            role="status"
            aria-live="polite"
          >
            {artifacts?.length ?? 0} artifacts found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div 
              className="space-y-2" 
              role="status" 
              aria-label="Loading artifacts"
              aria-busy="true"
            >
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
              <span className="sr-only">Loading artifact list, please wait...</span>
            </div>
          ) : artifacts && artifacts.length > 0 ? (
            <Table aria-labelledby="artifact-list-title" aria-describedby="artifact-count">
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Name</TableHead>
                  <TableHead scope="col">Type</TableHead>
                  <TableHead scope="col">ID</TableHead>
                  <TableHead scope="col" className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {artifacts.map((artifact) => {
                  const TypeIcon = typeIcons[artifact.type] || Package;
                  return (
                    <TableRow key={artifact.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <TypeIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                          <span className="font-medium">{artifact.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={typeColors[artifact.type]}>
                          {artifact.type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        <span aria-label={`ID: ${artifact.id}`}>
                          {artifact.id.slice(0, 8)}...
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="ghost" size="sm">
                          <Link 
                            to={`/artifacts/${artifact.type}/${artifact.id}`}
                            aria-label={`View details for ${artifact.name}`}
                          >
                            <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
                            View
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div 
              className="flex flex-col items-center justify-center py-12 text-center"
              role="status"
            >
              <Package className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
              <h3 className="mt-4 text-lg font-semibold">No artifacts found</h3>
              <p className="text-sm text-muted-foreground">
                {searchQuery
                  ? "Try a different search query"
                  : "Get started by uploading an artifact"}
              </p>
              <Button asChild className="mt-4">
                <Link to="/artifacts/new">
                  <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                  Upload Artifact
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
