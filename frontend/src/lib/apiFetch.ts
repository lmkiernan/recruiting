// In dev, if VITE_API_URL is not set, requests go to /api and Vite proxy handles them.
// In production, set VITE_API_URL=https://recruiter-dashboard-api.onrender.com
// with no trailing slash.

export const BASE = ((import.meta.env.VITE_API_URL as string | undefined) ?? "/api").replace(
  /\/$/,
  ""
);

function buildUrl(input: string): string {
  // Already absolute, leave it alone.
  if (input.startsWith("http://") || input.startsWith("https://")) {
    return input;
  }

  const normalizedInput = input.startsWith("/") ? input : `/${input}`;

  // If BASE is the production backend URL:
  // BASE=https://api.com, input=/api/candidates -> https://api.com/api/candidates
  if (BASE.startsWith("http")) {
    return `${BASE}${normalizedInput}`;
  }

  // Local dev:
  // BASE=/api, input=/candidates -> /api/candidates
  // BASE=/api, input=/api/candidates -> /api/candidates
  if (normalizedInput.startsWith(BASE)) {
    return normalizedInput;
  }

  return `${BASE}${normalizedInput}`;
}

export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const url = buildUrl(input);

  const res = await fetch(url, { credentials: "include", ...init }).catch(() => {
    throw new Error("Network error — could not reach the server");
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Request failed: ${res.status}`);
  }

  return res;
}