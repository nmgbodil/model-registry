const API_BASE_URL = "http://localhost:8000/api";

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export type ArtifactType = "model" | "dataset" | "code";

export interface ArtifactMetadata {
  name: string;
  id: string;
  type: ArtifactType;
}

export interface ArtifactData {
  url: string;
  download_url?: string;
}

export interface Artifact {
  metadata: ArtifactMetadata;
  data: ArtifactData;
}

export interface ModelRating {
  name: string;
  category: string;
  net_score: number;
  net_score_latency: number;
  ramp_up_time: number;
  ramp_up_time_latency: number;
  bus_factor: number;
  bus_factor_latency: number;
  performance_claims: number;
  performance_claims_latency: number;
  license: number;
  license_latency: number;
  dataset_and_code_score: number;
  dataset_and_code_score_latency: number;
  dataset_quality: number;
  dataset_quality_latency: number;
  code_quality: number;
  code_quality_latency: number;
  reproducibility: number;
  reproducibility_latency: number;
  reviewedness: number;
  reviewedness_latency: number;
  tree_score: number;
  tree_score_latency: number;
  size_score: {
    raspberry_pi: number;
    jetson_nano: number;
    desktop_pc: number;
    aws_server: number;
  };
  size_score_latency: number;
}

export interface ArtifactCost {
  standalone_cost?: number;
  total_cost: number;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  getToken() {
    return this.token;
  }

  async request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
    const { method = "GET", body, headers = {} } = options;

    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...headers,
    };

    if (this.token) {
      requestHeaders["X-Authorization"] = this.token;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: "Request failed" }));
      throw new Error(error.message || error.error || `HTTP ${response.status}`);
    }

    // Handle empty responses
    const text = await response.text();
    if (!text) return {} as T;
    
    return JSON.parse(text);
  }

  // Auth endpoints
  async login(name: string, password: string, isAdmin = false) {
    const response = await this.request<string>("/authenticate", {
      method: "PUT",
      body: { 
        user: { name, is_admin: isAdmin }, 
        secret: { password } 
      },
    });
    return response;
  }

  // Artifact endpoints
  async getArtifacts(queries?: Array<{ name: string; types?: ArtifactType[] }>, offset?: number) {
    const url = offset ? `/artifacts?offset=${offset}` : "/artifacts";
    return this.request<ArtifactMetadata[]>(url, {
      method: "POST",
      body: queries || [{ name: "*" }],
    });
  }

  async getArtifactById(artifactType: ArtifactType, id: string) {
    return this.request<Artifact>(`/artifacts/${artifactType}/${id}`);
  }

  async createArtifact(artifactType: ArtifactType, data: { url: string }) {
    return this.request<Artifact>(`/artifact/${artifactType}`, {
      method: "POST",
      body: data,
    });
  }

  async updateArtifact(artifactType: ArtifactType, id: string, data: Artifact) {
    return this.request(`/artifacts/${artifactType}/${id}`, {
      method: "PUT",
      body: data,
    });
  }

  async deleteArtifact(artifactType: ArtifactType, id: string) {
    return this.request(`/artifacts/${artifactType}/${id}`, { method: "DELETE" });
  }

  async getModelRating(id: string) {
    return this.request<ModelRating>(`/artifact/model/${id}/rate`);
  }

  async getArtifactCost(artifactType: ArtifactType, id: string, includeDependencies = false) {
    const url = includeDependencies 
      ? `/artifact/${artifactType}/${id}/cost?dependency=true` 
      : `/artifact/${artifactType}/${id}/cost`;
    return this.request<Record<string, ArtifactCost>>(url);
  }

  async searchArtifactsByRegex(regex: string) {
    return this.request<ArtifactMetadata[]>("/artifact/byRegEx", {
      method: "POST",
      body: { regex },
    });
  }

  async getArtifactHistory(artifactType: ArtifactType, name: string) {
    return this.request<Array<{
      user: { name: string; is_admin: boolean };
      date: string;
      artifact: ArtifactMetadata;
      action: string;
    }>>(`/artifact/${artifactType}/byName/${name}`);
  }

  // Reset
  async resetRegistry() {
    return this.request("/reset", { method: "DELETE" });
  }

  // Tracks
  async getTracks() {
    return this.request<{ plannedTracks: string[] }>("/tracks");
  }

  // Health
  async getHealth() {
    return this.request("/health");
  }
}

export const apiClient = new ApiClient();
