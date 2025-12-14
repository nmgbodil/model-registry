import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, ArtifactType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Loader2, Brain, Database, Code, Check } from "lucide-react";

const artifactTypes: { value: ArtifactType; label: string; icon: React.ElementType; description: string }[] = [
  { value: "model", label: "Model", icon: Brain, description: "Machine learning model from Hugging Face, etc." },
  { value: "dataset", label: "Dataset", icon: Database, description: "Training or evaluation dataset" },
  { value: "code", label: "Code", icon: Code, description: "Code repository from GitHub, etc." },
];

export default function ArtifactCreate() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [artifactType, setArtifactType] = useState<ArtifactType>("model");
  const [url, setUrl] = useState("");

  const createMutation = useMutation({
    mutationFn: async () => {
      return apiClient.createArtifact(artifactType, { url });
    },
    onSuccess: async () => {
      toast({
        title: "Artifact created successfully",
        description: "Your artifact is being processed and will appear in the list shortly.",
      });
      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
      
      // Small delay so user sees success state
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Always navigate to artifacts list since detail page may not be ready immediately
      navigate("/artifacts");
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      let title = "Failed to create artifact";
      let description = errorMessage;
      
      if (errorMessage.includes("409")) {
        title = "Artifact already exists";
        description = "This artifact has already been registered in the repository.";
      } else if (errorMessage.includes("400")) {
        title = "Invalid request";
        description = "Please check the URL format and artifact type.";
      } else if (errorMessage.includes("401")) {
        title = "Authentication required";
        description = "Please log in again to continue.";
      } else if (errorMessage.includes("403")) {
        title = "Permission denied";
        description = "You don't have permission to create artifacts.";
      }
      
      toast({
        variant: "destructive",
        title,
        description,
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url) {
      toast({
        variant: "destructive",
        title: "URL required",
        description: "Please enter an artifact source URL",
      });
      return;
    }

    createMutation.mutate();
  };

  const selectedType = artifactTypes.find(t => t.value === artifactType);

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
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload Artifact</h1>
          <p className="text-muted-foreground">
            Register a new model, dataset, or code to the registry
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle id="form-title">Artifact Details</CardTitle>
          <CardDescription id="form-description">
            Provide the source URL to register your artifact
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form 
            onSubmit={handleSubmit} 
            className="space-y-6"
            aria-labelledby="form-title"
            aria-describedby="form-description"
          >
            <div className="space-y-2">
              <Label htmlFor="type">
                Artifact Type <span className="text-destructive" aria-hidden="true">*</span>
                <span className="sr-only">(required)</span>
              </Label>
              <Select 
                value={artifactType} 
                onValueChange={(v) => setArtifactType(v as ArtifactType)}
              >
                <SelectTrigger 
                  id="type"
                  aria-required="true"
                  aria-describedby="type-description"
                >
                  <SelectValue placeholder="Select artifact type" />
                </SelectTrigger>
                <SelectContent>
                  {artifactTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <type.icon className="h-4 w-4" aria-hidden="true" />
                        <span>{type.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedType && (
                <p id="type-description" className="text-xs text-muted-foreground">
                  {selectedType.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="url">
                Source URL <span className="text-destructive" aria-hidden="true">*</span>
                <span className="sr-only">(required)</span>
              </Label>
              <Input
                id="url"
                type="url"
                placeholder={
                  artifactType === "model" 
                    ? "https://huggingface.co/google-bert/bert-base-uncased" 
                    : artifactType === "dataset"
                    ? "https://huggingface.co/datasets/squad"
                    : "https://github.com/openai/whisper"
                }
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                aria-required="true"
                aria-describedby="url-description"
              />
              <p id="url-description" className="text-xs text-muted-foreground">
                {artifactType === "model" && "Supports Hugging Face model URLs"}
                {artifactType === "dataset" && "Supports Hugging Face dataset URLs"}
                {artifactType === "code" && "Supports GitHub repository URLs"}
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/artifacts")}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={createMutation.isPending || createMutation.isSuccess}
                  aria-describedby={createMutation.isPending ? "upload-status" : undefined}
                >
                  {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                  {createMutation.isSuccess && <Check className="mr-2 h-4 w-4" aria-hidden="true" />}
                  {createMutation.isPending ? "Uploading..." : createMutation.isSuccess ? "Success!" : "Upload Artifact"}
                </Button>
              </div>
              {createMutation.isPending && (
                <p 
                  id="upload-status" 
                  className="text-sm text-muted-foreground animate-pulse"
                  role="status"
                  aria-live="polite"
                >
                  Processing artifact... This may take a minute.
                </p>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
