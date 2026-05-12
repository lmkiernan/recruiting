export const BASE = import.meta.env.PROD
  ? "https://recruiter-dashboard-api.onrender.com"
  : "/api";

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
