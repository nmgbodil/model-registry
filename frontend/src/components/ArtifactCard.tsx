import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileCode, Database, Brain, Calendar, TrendingUp } from "lucide-react";

export interface Artifact {
  id: string;
  name: string;
  type: "model" | "dataset" | "code";
  description?: string;
  version?: string;
  created_at?: string;
  net_score?: number;
}

interface ArtifactCardProps {
  artifact: Artifact;
}

const getTypeIcon = (type: string) => {
  switch (type) {
    case "model":
      return <Brain className="h-5 w-5" />;
    case "dataset":
      return <Database className="h-5 w-5" />;
    case "code":
      return <FileCode className="h-5 w-5" />;
    default:
      return null;
  }
};

const getTypeBadgeVariant = (type: string) => {
  switch (type) {
    case "model":
      return "default";
    case "dataset":
      return "secondary";
    case "code":
      return "outline";
    default:
      return "default";
  }
};

const ArtifactCard = ({ artifact }: ArtifactCardProps) => {
  return (
    <Link
      to={`/artifacts/${artifact.type}/${artifact.id}`} // ← fixed route
      className="block h-full"
    >
      <Card className="h-full transition-all hover:shadow-lg hover:border-accent cursor-pointer group">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-secondary text-secondary-foreground group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
                {getTypeIcon(artifact.type)}
              </div>
              <div className="space-y-1">
                <CardTitle className="text-lg group-hover:text-accent transition-colors">
                  {artifact.name}
                </CardTitle>
                <Badge variant={getTypeBadgeVariant(artifact.type)} className="capitalize">
                  {artifact.type}
                </Badge>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {artifact.description && (
            <CardDescription className="line-clamp-2">
              {artifact.description}
            </CardDescription>
          )}

          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            {artifact.version && (
              <div className="flex items-center gap-1.5">
                <span>v{artifact.version}</span>
              </div>
            )}
            {artifact.created_at && (
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                <span>{new Date(artifact.created_at).toLocaleDateString()}</span>
              </div>
            )}
            {artifact.net_score !== undefined && (
              <div className="flex items-center gap-1.5">
                <TrendingUp className="h-4 w-4" />
                <span>Score: {artifact.net_score.toFixed(2)}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};

export default ArtifactCard;
