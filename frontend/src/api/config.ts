import { OpenAPI } from "@/api/generated/client";

export function configureApi() {
  OpenAPI.BASE = import.meta.env.VITE_API_BASE || window.location.origin;
  OpenAPI.TOKEN = undefined; // no auth for 2.4; placeholder for later
  OpenAPI.WITH_CREDENTIALS = false;
  OpenAPI.HEADERS = {}; // we'll add per-call headers (e.g., offset) where needed
}
