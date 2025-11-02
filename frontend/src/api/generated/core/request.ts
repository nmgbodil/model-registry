import { OpenAPI } from '../client';

export async function request<T>(options: {
  method: string;
  url: string;
  headers?: Record<string, string>;
  body?: any;
}): Promise<T> {
  const headers: Record<string, string> = {
    ...OpenAPI.HEADERS,
    ...options.headers,
  };

  if (OpenAPI.TOKEN) {
    headers['Authorization'] = `Bearer ${OpenAPI.TOKEN}`;
  }

  const url = `${OpenAPI.BASE}${options.url}`;

  const config: RequestInit = {
    method: options.method,
    headers,
    credentials: OpenAPI.WITH_CREDENTIALS ? 'include' : 'same-origin',
  };

  if (options.body) {
    if (options.body instanceof FormData) {
      config.body = options.body;
    } else {
      headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(options.body);
    }
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  // Store response headers for pagination
  const nextOffset = response.headers.get('x-next-offset');
  if (nextOffset) {
    (response as any).nextOffset = parseInt(nextOffset, 10);
  }

  return response.json();
}
