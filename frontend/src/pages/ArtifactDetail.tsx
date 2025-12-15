import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, ArtifactType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Package,
  Star,
  DollarSign,
  Trash2,
  ArrowLeft,
  ExternalLink,
  Clock,
  Shield,
  Users,
  Brain,
  Database,
  Code,
  CheckCircle,
  BarChart3,
  FileCode,
  RefreshCw,
  Eye,
  TreeDeciduous,
  HardDrive,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

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

function RatingCard({ label, score, latency, icon: Icon }: { label: string; score: number; latency?: number; icon: React.ElementType }) {
  const getScoreColor = (score: number) => {
    if (score >= 0.7) return "text-green-700";
    if (score >= 0.4) return "text-yellow-700";
    return "text-red-700";
  };

  const getScoreDescription = (score: number) => {
    if (score >= 0.7) return "Good";
    if (score >= 0.4) return "Fair";
    return "Poor";
  };

  const scorePercent = (score * 100).toFixed(0);

  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium">{label}</p>
          {latency !== undefined && (
            <p className="text-xs text-muted-foreground">{latency.toFixed(2)}s</p>
          )}
        </div>
      </div>
      <span 
        className={`text-lg font-bold ${getScoreColor(score)}`}
        aria-label={`${label}: ${scorePercent}% (${getScoreDescription(score)})`}
      >
        {scorePercent}%
      </span>
    </div>
  );
}

export default function ArtifactDetail() {
  const { type, id } = useParams<{ type: ArtifactType; id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const artifactType = type as ArtifactType;

  const { 
    data: artifactData, 
    isLoading: artifactLoading, 
    isError: artifactError, 
    error: artifactErrorData, 
    refetch, 
    isFetching,
    failureCount,
  } = useQuery({
    queryKey: ["artifact", artifactType, id],
    queryFn: () => apiClient.getArtifactById(artifactType, id!),
    enabled: !!id && !!artifactType,
    retry: (failureCount, error) => {
      // Retry up to 3 times for 404 errors (backend may still be processing)
      if (error instanceof Error && error.message.includes("404") && failureCount < 3) {
        return true;
      }
      return false;
    },
    retryDelay: 2000, // Wait 2 seconds between retries
  });

  // Only fetch ratings for model artifacts
  const { data: rating, isLoading: ratingLoading } = useQuery({
    queryKey: ["model-rating", id],
    queryFn: () => apiClient.getModelRating(id!),
    enabled: !!id && artifactType === "model",
  });

  const { data: cost, isLoading: costLoading } = useQuery({
    queryKey: ["artifact-cost", artifactType, id],
    queryFn: () => apiClient.getArtifactCost(artifactType, id!, true),
    enabled: !!id && !!artifactType,
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteArtifact(artifactType, id!),
    onSuccess: () => {
      toast({ title: "Artifact deleted successfully" });
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      navigate("/artifacts");
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Failed to delete artifact",
        description: error instanceof Error ? error.message : "Unknown error",
      });
    },
  });

  // Detect if we're retrying after a failure
  const isRetrying = isFetching && failureCount > 0;

  // Show skeleton only for initial load (not during retries)
  if (artifactLoading && !isRetrying) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading artifact details">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
        <span className="sr-only">Loading artifact details, please wait...</span>
      </div>
    );
  }

  // Show processing message during retries
  if (isRetrying) {
    return (
      <div 
        className="flex flex-col items-center justify-center py-12"
        role="status"
        aria-live="polite"
      >
        <Package className="h-12 w-12 text-muted-foreground/50 animate-pulse" aria-hidden="true" />
        <h2 className="mt-4 text-lg font-semibold">Artifact Processing</h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-md text-center">
          This artifact is still being processed. Checking again...
        </p>
        <RefreshCw className="mt-4 h-6 w-6 animate-spin text-primary" aria-hidden="true" />
        <p className="mt-2 text-xs text-muted-foreground">
          Retry {failureCount} of 3
        </p>
      </div>
    );
  }

  if (artifactError || !artifactData) {
    const errorMessage = artifactErrorData instanceof Error 
      ? artifactErrorData.message 
      : "Artifact not found";
    const is404 = errorMessage.includes("404");
    
    return (
      <div 
        className="flex flex-col items-center justify-center py-12"
        role="alert"
        aria-live="assertive"
      >
        <Package className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
        <h2 className="mt-4 text-lg font-semibold">
          {is404 ? "Artifact Still Processing" : "Failed to load artifact"}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-md text-center">
          {is404 
            ? "This artifact is still being processed by the backend. Please wait a moment and try again."
            : errorMessage}
        </p>
        <div className="flex gap-2 mt-4">
          <Button 
            variant="outline" 
            onClick={() => refetch()} 
            disabled={isFetching}
            aria-label={isFetching ? "Retrying, please wait" : "Retry loading artifact"}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} aria-hidden="true" />
            {isFetching ? "Retrying..." : "Retry"}
          </Button>
          <Button onClick={() => navigate("/artifacts")}>
            Back to Artifacts
          </Button>
        </div>
      </div>
    );
  }

  const { metadata, data } = artifactData;
  const TypeIcon = typeIcons[metadata.type] || Package;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => navigate("/artifacts")}
          aria-label="Go back to artifacts list"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <TypeIcon className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
            <h1 className="text-3xl font-bold tracking-tight">{metadata.name}</h1>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="outline" className={typeColors[metadata.type]}>
              {metadata.type}
            </Badge>
            <span className="text-sm text-muted-foreground font-mono">
              ID: {metadata.id}
            </span>
          </div>
        </div>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" size="sm">
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              Delete
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Artifact</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete "{metadata.name}"? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => deleteMutation.mutate()}>
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          {metadata.type === "model" && (
            <TabsTrigger value="ratings">Ratings</TabsTrigger>
          )}
          <TabsTrigger value="cost">Cost</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Artifact Information</CardTitle>
              <CardDescription>Details about this artifact</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.url && (
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium">Source URL</p>
                    <a
                      href={data.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline flex items-center gap-1"
                    >
                      {data.url}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              )}
              {data.download_url && (
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium">Download URL</p>
                    <a
                      href={data.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline flex items-center gap-1"
                    >
                      {data.download_url}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {metadata.type === "model" && (
          <TabsContent value="ratings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5" />
                  Model Ratings
                </CardTitle>
                <CardDescription>Quality and reliability metrics</CardDescription>
              </CardHeader>
              <CardContent>
                {ratingLoading ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {[...Array(8)].map((_, i) => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : rating ? (
                  <div className="space-y-6">
                    <div className="rounded-lg bg-muted/50 p-4 text-center">
                      <p className="text-sm text-muted-foreground">Net Score</p>
                      <p className="text-4xl font-bold text-primary">
                        {(rating.net_score * 100).toFixed(0)}%
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Latency: {rating.net_score_latency.toFixed(2)}s
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {rating.name} • {rating.category}
                      </p>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <RatingCard
                        label="Bus Factor"
                        score={rating.bus_factor}
                        latency={rating.bus_factor_latency}
                        icon={Users}
                      />
                      <RatingCard
                        label="Ramp Up Time"
                        score={rating.ramp_up_time}
                        latency={rating.ramp_up_time_latency}
                        icon={Clock}
                      />
                      <RatingCard
                        label="Performance Claims"
                        score={rating.performance_claims}
                        latency={rating.performance_claims_latency}
                        icon={BarChart3}
                      />
                      <RatingCard
                        label="License"
                        score={rating.license}
                        latency={rating.license_latency}
                        icon={Shield}
                      />
                      <RatingCard
                        label="Dataset & Code Score"
                        score={rating.dataset_and_code_score}
                        latency={rating.dataset_and_code_score_latency}
                        icon={FileCode}
                      />
                      <RatingCard
                        label="Dataset Quality"
                        score={rating.dataset_quality}
                        latency={rating.dataset_quality_latency}
                        icon={Database}
                      />
                      <RatingCard
                        label="Code Quality"
                        score={rating.code_quality}
                        latency={rating.code_quality_latency}
                        icon={Code}
                      />
                      <RatingCard
                        label="Reproducibility"
                        score={rating.reproducibility}
                        latency={rating.reproducibility_latency}
                        icon={RefreshCw}
                      />
                      <RatingCard
                        label="Reviewedness"
                        score={rating.reviewedness}
                        latency={rating.reviewedness_latency}
                        icon={Eye}
                      />
                      <RatingCard
                        label="Tree Score"
                        score={rating.tree_score}
                        latency={rating.tree_score_latency}
                        icon={TreeDeciduous}
                      />
                    </div>

                    {rating.size_score && (
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium flex items-center gap-2">
                          <HardDrive className="h-4 w-4" />
                          Size Suitability Scores
                        </h4>
                        <div className="grid gap-3 md:grid-cols-2">
                          <RatingCard
                            label="Raspberry Pi"
                            score={rating.size_score.raspberry_pi}
                            icon={HardDrive}
                          />
                          <RatingCard
                            label="Jetson Nano"
                            score={rating.size_score.jetson_nano}
                            icon={HardDrive}
                          />
                          <RatingCard
                            label="Desktop PC"
                            score={rating.size_score.desktop_pc}
                            icon={HardDrive}
                          />
                          <RatingCard
                            label="AWS Server"
                            score={rating.size_score.aws_server}
                            icon={HardDrive}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Rating information not available
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        <TabsContent value="cost" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Artifact Cost
              </CardTitle>
              <CardDescription>Size and dependency costs (in MB)</CardDescription>
            </CardHeader>
            <CardContent>
              {costLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : cost ? (
                <div className="space-y-4">
                  {Object.entries(cost).map(([artifactId, costData]) => (
                    <div key={artifactId} className="rounded-lg border p-4">
                      <p className="text-sm font-medium font-mono">{artifactId}</p>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {costData.standalone_cost !== undefined && (
                          <div>
                            <p className="text-xs text-muted-foreground">Standalone Cost</p>
                            <p className="text-lg font-semibold">
                              {costData.standalone_cost.toFixed(2)} MB
                            </p>
                          </div>
                        )}
                        <div>
                          <p className="text-xs text-muted-foreground">Total Cost</p>
                          <p className="text-lg font-semibold">
                            {costData.total_cost.toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Cost information not available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
