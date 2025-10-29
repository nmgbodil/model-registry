import { OpenAPI } from "./core/OpenAPI";

// Base URL where your backend is running in dev.
// If your backend runs on a different port (e.g. 3000, 8080), change it here.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// We'll keep an auth token in module scope.
// Later, after login, you'll call setAuthToken("the-jwt").
let authToken: string | undefined;

export function setAuthToken(token: string | undefined) {
  authToken = token;
  // Set OpenAPI.TOKEN to a string when we have a token so it matches the
  // generated typing (TOKEN?: string | Resolver<string>).
  OpenAPI.TOKEN = token ? `Bearer ${token}` : undefined;
}

// Configure the global OpenAPI client that the generated services use.
OpenAPI.BASE = API_BASE_URL;

// If your backend requires cookies / session-based auth later, flip this:
OpenAPI.WITH_CREDENTIALS = false;

// We set `OpenAPI.TOKEN` inside `setAuthToken()` above so it matches the
// generated `OpenAPI` typing (it accepts a string or a resolver).

// Re-export so other code can import { OpenAPI } if needed
export { OpenAPI };
