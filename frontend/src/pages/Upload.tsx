import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload as UploadIcon, FileArchive, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

const Upload = () => {
  const navigate = useNavigate();
  const [artifactType, setArtifactType] = useState<string>("");
  const [artifactName, setArtifactName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.zip')) {
        setFile(selectedFile);
      } else {
        toast.error("Please select a .zip file");
        e.target.value = "";
      }
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!artifactType || !artifactName || !file) {
      toast.error("Please fill in all required fields");
      return;
    }
    
    setIsUploading(true);
    
    // Simulate upload process
    setTimeout(() => {
      setIsUploading(false);
      setUploadSuccess(true);
      toast.success("Artifact uploaded successfully!", {
        description: `${artifactName} has been added to the registry`,
      });
      
      // Reset form after 2 seconds and navigate
      setTimeout(() => {
        navigate("/");
      }, 2000);
    }, 2000);
  };
  
  if (uploadSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="max-w-md w-full text-center">
          <CardHeader>
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <CardTitle>Upload Successful!</CardTitle>
            <CardDescription>
              Your artifact has been successfully uploaded to the registry
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/")} className="w-full">
              View All Artifacts
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Upload Artifact</h1>
          <p className="text-muted-foreground text-lg">
            Add a new model, dataset, or code repository to the registry
          </p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Artifact Details</CardTitle>
            <CardDescription>
              Provide information about the artifact you're uploading
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Artifact Type */}
              <div className="space-y-2">
                <Label htmlFor="type">
                  Artifact Type <span className="text-destructive">*</span>
                </Label>
                <Select value={artifactType} onValueChange={setArtifactType}>
                  <SelectTrigger id="type">
                    <SelectValue placeholder="Select artifact type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="model">Model</SelectItem>
                    <SelectItem value="dataset">Dataset</SelectItem>
                    <SelectItem value="code">Code</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Artifact Name */}
              <div className="space-y-2">
                <Label htmlFor="name">
                  Artifact Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  placeholder="e.g., ResNet-50 Image Classifier"
                  value={artifactName}
                  onChange={(e) => setArtifactName(e.target.value)}
                  required
                />
              </div>
              
              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Provide a brief description of your artifact..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                />
              </div>
              
              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="file">
                  Upload File (.zip) <span className="text-destructive">*</span>
                </Label>
                <div className="flex items-center gap-4">
                  <Input
                    id="file"
                    type="file"
                    accept=".zip"
                    onChange={handleFileChange}
                    className="cursor-pointer"
                    required
                  />
                  {file && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <FileArchive className="h-4 w-4" />
                      <span className="truncate max-w-[200px]">{file.name}</span>
                    </div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Only .zip files are accepted. Maximum file size: 500MB
                </p>
              </div>
              
              {/* Info Box */}
              <div className="flex gap-3 rounded-lg border border-border bg-muted/50 p-4">
                <AlertCircle className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <p className="font-medium text-foreground mb-1">Before uploading</p>
                  <p>Ensure your artifact is properly packaged and includes all necessary dependencies and documentation.</p>
                </div>
              </div>
              
              {/* Submit Button */}
              <div className="flex gap-4">
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <>
                      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <UploadIcon className="mr-2 h-4 w-4" />
                      Upload Artifact
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/")}
                  disabled={isUploading}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Upload;
