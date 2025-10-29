import { useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import ArtifactCard from "@/components/ArtifactCard";
import { mockArtifacts } from "@/data/mockArtifacts";

const Artifacts = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [displayCount, setDisplayCount] = useState(6);
  
  const filteredArtifacts = mockArtifacts.filter(artifact =>
    artifact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    artifact.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    artifact.type.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  const displayedArtifacts = filteredArtifacts.slice(0, displayCount);
  const hasMore = displayCount < filteredArtifacts.length;
  
  return (
    <div className="min-h-screen">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="mb-8 space-y-4">
          <div>
            <h1 className="text-4xl font-bold mb-2">Artifacts</h1>
            <p className="text-muted-foreground text-lg">
              Browse and manage your machine learning models, datasets, and code repositories
            </p>
          </div>
          
          {/* Search Bar */}
          <div className="flex gap-4 max-w-2xl">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search artifacts by name, type, or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          {/* Stats */}
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-muted-foreground">Total Artifacts: </span>
              <span className="font-semibold">{mockArtifacts.length}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Models: </span>
              <span className="font-semibold">{mockArtifacts.filter(a => a.type === "model").length}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Datasets: </span>
              <span className="font-semibold">{mockArtifacts.filter(a => a.type === "dataset").length}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Code: </span>
              <span className="font-semibold">{mockArtifacts.filter(a => a.type === "code").length}</span>
            </div>
          </div>
        </div>
        
        {/* Artifacts Grid */}
        {displayedArtifacts.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-lg">No artifacts found matching your search</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {displayedArtifacts.map((artifact) => (
                <ArtifactCard key={artifact.id} artifact={artifact} />
              ))}
            </div>
            
            {/* Load More Button */}
            {hasMore && (
              <div className="flex justify-center">
                <Button
                  onClick={() => setDisplayCount(prev => prev + 6)}
                  variant="outline"
                  size="lg"
                >
                  Load More Artifacts
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Artifacts;
