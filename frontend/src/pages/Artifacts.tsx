import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import ArtifactCard from "../components/ArtifactCard";

import { OpenAPI } from "../api/generated/client";
import { DefaultService } from "../api/generated/services/DefaultService";

const Artifacts = () => {
  // search text from the input box
  const [searchQuery, setSearchQuery] = useState("");

  // pagination control
  const [offset, setOffset] = useState(0);
  const limit = 6; // we will simulate page size locally

  // point OpenAPI at your backend
  // NOTE: change this port if your backend isn't on 8000
  OpenAPI.BASE = "http://localhost:8000";

  // TODO later: after login, you'll store a real token in state/context
  // and pass it here instead of "dev-token".
  const xAuthorization = "dev-token";

  const { data, isLoading, isError } = useQuery({
    queryKey: ["artifacts", { searchQuery, offset, limit }],
    queryFn: async () => {
      if (searchQuery.trim() !== "") {
        // regex search flow
        return DefaultService.artifactByRegExGet({
          xAuthorization,
          requestBody: {
            // This MUST match ArtifactRegEx in src/api/generated/models/ArtifactRegEx.ts
            // Open that file and check the field name. Common names are:
            //   { regex: string }
            //   { pattern: string }
            // I'll assume it's { regex: string } for now:
            regex: searchQuery,
          },
        });
      }

      // listing / enumeration flow
      return DefaultService.artifactsList({
        xAuthorization,
        requestBody: [
          {
            // This MUST match ArtifactQuery in src/api/generated/models/ArtifactQuery.ts
            // At minimum we know from the comment that name: "*" is valid to get everything.
            name: "*",
          },
        ],
        // backend supports pagination via `offset` returned in headers;
        // we'll pass our current offset. We'll simulate 'limit' on the client for now,
        // since the spec doesn't expose limit here.
          offset: offset.toString(), 
      });
    },
  });

  // data is an Array<ArtifactMetadata> per your service defs
  const allArtifacts = Array.isArray(data) ? data : [];

  // we'll slice client-side to mimic "limit" until backend exposes page size
  const artifactsPage = allArtifacts.slice(0, limit);

  const totalCount = allArtifacts.length;
  const modelCount = allArtifacts.filter((a: any) => a.type === "model").length;
  const datasetCount = allArtifacts.filter((a: any) => a.type === "dataset").length;
  const codeCount = allArtifacts.filter((a: any) => a.type === "code").length;

  const handleLoadMore = () => {
    // bump pagination offset for the NEXT query
    setOffset((prev) => prev + limit);
  };

  const hasMore = totalCount > artifactsPage.length;

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
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  // reset pagination when the query changes
                  setOffset(0);
                }}
                className="pl-10"
              />
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-muted-foreground">Total Artifacts: </span>
              <span className="font-semibold">{totalCount}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Models: </span>
              <span className="font-semibold">{modelCount}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Datasets: </span>
              <span className="font-semibold">{datasetCount}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Code: </span>
              <span className="font-semibold">{codeCount}</span>
            </div>
          </div>
        </div>

        {/* Loading / Error */}
        {isLoading && (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-lg">Loading artifacts…</p>
          </div>
        )}

        {isError && !isLoading && (
          <div className="text-center py-16">
            <p className="text-red-500 text-lg">Failed to load artifacts from server.</p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !isError && artifactsPage.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-lg">
              {searchQuery
                ? "No artifacts matched that search."
                : "No artifacts in the registry yet."}
            </p>
          </div>
        ) : null}

        {/* Results grid */}
        {!isLoading && !isError && artifactsPage.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {artifactsPage.map((artifact: any) => (
                <ArtifactCard key={artifact.id} artifact={artifact} />
              ))}
            </div>

            {hasMore && (
              <div className="flex justify-center">
                <Button
                  onClick={handleLoadMore}
                  variant="outline"
                  size="lg"
                >
                  Load More Artifacts
                </Button>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
};

export default Artifacts;
