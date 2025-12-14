import { Link, useLocation } from "react-router-dom";
import { Package, Upload, Search, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/client";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

const Navigation = () => {
  const location = useLocation();
  const { toast } = useToast();
  
  const isActive = (path: string) => location.pathname === path;
  
  // Health check query
  const { data: healthStatus, isError, refetch, isFetching } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const response = await fetch(`${OpenAPI.BASE}/health`);
      if (!response.ok) throw new Error("Health check failed");
      return { status: "ok" };
    },
    refetchInterval: 30000, // Check every 30 seconds
    retry: 1,
  });
  
  const handleHealthCheck = async () => {
    const result = await refetch();
    if (result.isError) {
      toast({
        title: "Service Unreachable",
        description: "The backend API is not responding.",
        variant: "destructive",
      });
    } else {
      toast({
        title: "Service Healthy",
        description: "The backend API is operational.",
      });
    }
  };
  
  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2 text-xl font-bold text-foreground hover:text-primary transition-colors">
              <Package className="h-6 w-6" />
              <span>Model Registry</span>
            </Link>
            
            <div className="hidden md:flex items-center gap-1">
              <Link
                to="/"
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive("/")
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                Browse
              </Link>
              <Link
                to="/upload"
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2",
                  isActive("/upload")
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <Upload className="h-4 w-4" />
                Upload
              </Link>
              <Link
                to="/search"
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2",
                  isActive("/search")
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                <Search className="h-4 w-4" />
                Search
              </Link>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleHealthCheck}
              disabled={isFetching}
              className="gap-2"
              title="Backend API Health Status"
            >
              <Activity 
                className={cn(
                  "h-4 w-4 transition-colors",
                  isError ? "text-destructive" : "text-green-500",
                  isFetching && "animate-pulse"
                )}
              />
              <span className="text-xs hidden sm:inline">
                {isFetching ? "Checking..." : isError ? "Offline" : "Online"}
              </span>
            </Button>
            <span className="text-xs text-muted-foreground hidden md:inline">MVP v0.1</span>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
