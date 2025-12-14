export interface User {
  name: string;
  isAdmin: boolean;
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

export interface ArtifactAuditEntry {
  user: User;
  date: string;
  artifact: ArtifactMetadata;
  action: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}
