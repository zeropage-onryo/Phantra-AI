/* The ad-results routes (app/api.py, src/ad_results.py). Types and the pure
   helpers live in lib/ad-results.ts. */
import { API_URL, ApiError, apiFetch } from "@/lib/api";
import { GUARDED_HEADERS } from "@/lib/studio-api";
import type { AdResults, ImportResult } from "@/lib/ad-results";

export const getAdResults = () => apiFetch<AdResults>("/ad-results");

export async function importAdReport(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  // no Content-Type: the browser writes the multipart boundary itself
  const res = await fetch(`${API_URL}/api/ad-results/import`, {
    method: "POST",
    credentials: "include",
    headers: GUARDED_HEADERS,
    body: form,
  });
  if (!res.ok) {
    let message = res.statusText || `request failed (${res.status})`;
    let code: string | undefined;
    try {
      const body = await res.clone().json();
      message = body?.error?.message ?? body?.detail ?? message;
      code = body?.error?.code;
    } catch {
      // not JSON -- keep the fallback
    }
    throw new ApiError(message, res.status, code);
  }
  return (await res.json()) as ImportResult;
}

export const deleteAdImport = (importId: string) =>
  apiFetch<{ deleted: number }>(`/ad-results/imports/${encodeURIComponent(importId)}`, {
    method: "DELETE",
    headers: GUARDED_HEADERS,
  });
