import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import { DefaultService } from "@/api/generated/services/DefaultService";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/hooks/use-toast";
import { Upload as UploadIcon, Loader2 } from "lucide-react";

interface UploadFormData {
  type: "model" | "dataset" | "code";
  name: string;
  version: string;
  description: string;
  url: string;
}

export default function UploadPage() {
  const { register, handleSubmit, formState: { errors }, reset, setValue, watch } = useForm<UploadFormData>();
  const [selectedType, setSelectedType] = useState<"model" | "dataset" | "code">("model");

  const uploadMutation = useMutation({
    mutationFn: async (data: UploadFormData) => {
      return DefaultService.artifactCreate(data.type, {
        name: data.name,
        version: data.version,
        description: data.description,
        url: data.url,
      });
    },
    onSuccess: () => {
      toast({
        title: "Upload successful",
        description: "Your artifact has been uploaded successfully.",
      });
      reset();
    },
    onError: (error: Error) => {
      toast({
        title: "Upload failed",
        description: error.message || "Failed to upload artifact. Please try again.",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: UploadFormData) => {
    uploadMutation.mutate(data);
  };

  return (
    <div className="container max-w-2xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Upload Artifact</h1>
        <p className="text-muted-foreground">
          Upload a new model, dataset, or code artifact to the registry
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 bg-card p-6 rounded-lg border">
        <div className="space-y-2">
          <Label htmlFor="type">Type *</Label>
          <Select
            value={selectedType}
            onValueChange={(value: "model" | "dataset" | "code") => {
              setSelectedType(value);
              setValue("type", value);
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select artifact type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="model">Model</SelectItem>
              <SelectItem value="dataset">Dataset</SelectItem>
              <SelectItem value="code">Code</SelectItem>
            </SelectContent>
          </Select>
          <input type="hidden" {...register("type", { required: true })} value={selectedType} />
          {errors.type && <p className="text-sm text-destructive">Type is required</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="name">Name *</Label>
          <Input
            id="name"
            {...register("name", { required: "Name is required" })}
            placeholder="e.g., sentiment-classifier"
          />
          {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="version">Version</Label>
          <Input
            id="version"
            {...register("version")}
            placeholder="e.g., 1.0.0"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            {...register("description")}
            placeholder="Describe your artifact..."
            rows={4}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="url">URL *</Label>
          <Input
            id="url"
            type="url"
            {...register("url", { 
              required: "URL is required",
              pattern: {
                value: /^https?:\/\/.+/,
                message: "Please enter a valid URL"
              }
            })}
            placeholder="https://example.com/artifact.zip"
          />
          {errors.url && <p className="text-sm text-destructive">{errors.url.message}</p>}
        </div>

        <Button
          type="submit"
          disabled={uploadMutation.isPending}
          className="w-full"
          aria-busy={uploadMutation.isPending}
        >
          {uploadMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <UploadIcon className="mr-2 h-4 w-4" />
              Upload Artifact
            </>
          )}
        </Button>
      </form>
    </div>
  );
}
