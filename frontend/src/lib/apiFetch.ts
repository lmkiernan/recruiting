// In dev the Vite proxy strips "/api" and forwards to localhost:8000.
// In production set VITE_API_URL=https://recruiter-dashboard-api.onrender.com (no trailing slash).
export const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, { credentials: "include", ...init }).catch(() => {
    throw new Error("Network error — could not reach the server");
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Request failed: ${res.status}`);
  }
  return res;
}
