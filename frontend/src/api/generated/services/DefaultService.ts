import { request } from '../core/request';

export interface Artifact {
  id: string;
  name: string;
  type: 'model' | 'dataset' | 'code';
  version?: string;
  description?: string;
  created_at?: string;
  net_score?: number;
}

export class DefaultService {
  /**
   * Upload artifact
   */
  public static async artifactCreate(
    type: 'model' | 'dataset' | 'code',
    body: {
      name: string;
      version?: string;
      description?: string;
      url: string;
    }
  ): Promise<Artifact> {
    return request<Artifact>({
      method: 'POST',
      url: `/artifact/${type}`,
      body,
    });
  }

  /**
   * List artifacts with pagination
   */
  public static async artifactsList(params?: {
    limit?: number;
    type?: string;
  }): Promise<Artifact[]> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.set('limit', String(params.limit));
    if (params?.type && params.type !== 'all') queryParams.set('type', params.type);
    
    const queryString = queryParams.toString();
    const url = `/artifacts${queryString ? `?${queryString}` : ''}`;
    
    return request<Artifact[]>({
      method: 'POST',
      url,
    });
  }

  /**
   * Search artifacts by regex
   */
  public static async artifactByRegExGet(params: {
    pattern: string;
    type?: string;
    limit?: number;
  }): Promise<Artifact[]> {
    const queryParams = new URLSearchParams();
    queryParams.set('pattern', params.pattern);
    if (params.type && params.type !== 'all') queryParams.set('type', params.type);
    if (params.limit) queryParams.set('limit', String(params.limit));
    
    return request<Artifact[]>({
      method: 'GET',
      url: `/artifact/by-regex?${queryParams.toString()}`,
    });
  }

  /**
   * Create auth token (placeholder for future)
   */
  public static async createAuthToken(body: {
    username: string;
    password: string;
  }): Promise<{ access_token: string }> {
    return request({
      method: 'POST',
      url: '/auth/token',
      body,
    });
  }

  /**
   * Get artifact details
   */
  public static async artifactGet(id: string): Promise<Artifact> {
    return request<Artifact>({
      method: 'GET',
      url: `/artifact/${id}`,
    });
  }

  /**
   * Delete artifact
   */
  public static async artifactDelete(id: string): Promise<void> {
    return request<void>({
      method: 'DELETE',
      url: `/artifact/${id}`,
    });
  }
}