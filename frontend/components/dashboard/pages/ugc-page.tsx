"use client";

import { useEffect, useMemo, useState } from "react";
import { clearAuthToken, getAuthToken } from "@/lib/auth";

type UgcResponse = {
  success: boolean;
  runId?: string;
  message?: string;
  workflowResponse?: unknown;
  error?: { message?: string } | string;
};

type UgcVariant = {
  index?: number | string;
  videoUrl?: string;
  downloadUrl?: string;
  videoKey?: string;
  extendedUrl?: string;
};

type UgcRun = {
  id: string;
  productName: string;
  language?: string | null;
  status: string;
  createdAt?: string;
  updatedAt?: string;
  variants?: UgcVariant[];
  error?: string | null;
};

export function UgcPage() {
  const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024;
  const [productName, setProductName] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("English (US)");
  const [creatorLocationStyle, setCreatorLocationStyle] = useState("US creator");
  const [description, setDescription] = useState("");
  const [productImageUrl, setProductImageUrl] = useState("");
  const [productImageFile, setProductImageFile] = useState<File | null>(null);
  const [productImageFileName, setProductImageFileName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UgcResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<UgcRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const hasProcessingRuns = useMemo(
    () => runs.some((run) => run.status === "processing"),
    [runs],
  );

  const normalizedWorkflowResponse = useMemo(() => {
    if (!result?.workflowResponse) return null;
    if (typeof result.workflowResponse === "string") {
      try {
        return JSON.parse(result.workflowResponse) as Record<string, unknown>;
      } catch {
        return { raw: result.workflowResponse } as Record<string, unknown>;
      }
    }
    if (typeof result.workflowResponse === "object") {
      return result.workflowResponse as Record<string, unknown>;
    }
    return { raw: String(result.workflowResponse) } as Record<string, unknown>;
  }, [result]);

  async function fetchRuns() {
    const token = getAuthToken();
    if (!token) return;
    try {
      setLoadingRuns(true);
      const baseUrl = process.env.NEXT_PUBLIC_BRAND_MONITOR_URL || "http://localhost:4001";
      const response = await fetch(`${baseUrl}/api/brand-monitor/ugc/runs`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.status === 401) {
        clearAuthToken();
        window.location.href = "/login";
        return;
      }
      const data = (await response.json().catch(() => [])) as UgcRun[];
      setRuns(Array.isArray(data) ? data : []);
    } catch {
      // Silent; user still sees form + last known data.
    } finally {
      setLoadingRuns(false);
    }
  }

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    if (!hasProcessingRuns) return;
    const interval = window.setInterval(() => {
      fetchRuns();
    }, 8000);
    return () => window.clearInterval(interval);
  }, [hasProcessingRuns]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    const token = getAuthToken();
    if (!token) {
      setError("Authentication required. Please login again.");
      return;
    }

    try {
      setLoading(true);
      const baseUrl = process.env.NEXT_PUBLIC_BRAND_MONITOR_URL || "http://localhost:4001";
      const formData = new FormData();
      formData.append("productName", productName);
      formData.append("targetLanguage", targetLanguage);
      formData.append("creatorLocationStyle", creatorLocationStyle);
      if (description.trim()) formData.append("description", description.trim());
      if (productImageUrl.trim()) formData.append("productImageUrl", productImageUrl.trim());
      if (productImageFile) formData.append("file", productImageFile, productImageFile.name);

      const response = await fetch(`${baseUrl}/api/brand-monitor/ugc/generate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = (await response.json().catch(() => ({}))) as UgcResponse;
      if (!response.ok) {
        const message =
          (typeof data.error === "string" ? data.error : data.error?.message) ||
          "Failed to trigger UGC workflow";
        throw new Error(message);
      }
      setResult(data);
      fetchRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger UGC workflow");
    } finally {
      setLoading(false);
    }
  }

  function handleImageUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      setProductImageFile(null);
      setProductImageFileName(null);
      return;
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setError("Image is too large. Please upload an image up to 4MB.");
      setProductImageFile(null);
      setProductImageFileName(null);
      event.target.value = "";
      return;
    }

    setProductImageFile(file);
    setProductImageFileName(file.name);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h2 className="text-base font-semibold text-foreground">Create UGC via n8n</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          This triggers your Product-to-UGC n8n workflow using backend webhook integration.
        </p>

        <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
          <label className="grid gap-2 text-xs font-medium text-foreground">
            Product name
            <input
              value={productName}
              onChange={(event) => setProductName(event.target.value)}
              placeholder="Hydrating Face Serum"
              required
              className="h-10 rounded-lg border border-border bg-background px-3 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-xs font-medium text-foreground">
              Target language / region
              <input
                value={targetLanguage}
                onChange={(event) => setTargetLanguage(event.target.value)}
                className="h-10 rounded-lg border border-border bg-background px-3 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
              />
            </label>
            <label className="grid gap-2 text-xs font-medium text-foreground">
              Creator location style
              <input
                value={creatorLocationStyle}
                onChange={(event) => setCreatorLocationStyle(event.target.value)}
                className="h-10 rounded-lg border border-border bg-background px-3 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
              />
            </label>
          </div>

          <label className="grid gap-2 text-xs font-medium text-foreground">
            Ad description (optional)
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Short UGC brief, key points, hooks, CTA..."
              rows={3}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="grid gap-2 text-xs font-medium text-foreground">
            Product image URL (optional)
            <input
              type="url"
              value={productImageUrl}
              onChange={(event) => setProductImageUrl(event.target.value)}
              placeholder="https://example.com/product.jpg"
              className="h-10 rounded-lg border border-border bg-background px-3 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <label className="grid gap-2 text-xs font-medium text-foreground">
            Upload product image (optional)
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="h-10 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
            />
            {productImageFileName && (
              <span className="text-[11px] text-muted-foreground">Selected: {productImageFileName}</span>
            )}
          </label>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? "Triggering..." : "Trigger UGC Workflow"}
          </button>
        </form>
      </section>

      {error && (
        <section className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {error}
        </section>
      )}

      {result && (
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-foreground">Workflow Response</h3>
          <div className="mt-3 grid gap-2 text-xs">
            <div className="rounded-lg border border-border bg-background p-3">
              <p className="text-[11px] text-muted-foreground">Run ID</p>
              <p className="font-mono text-foreground">{result.runId || "N/A"}</p>
            </div>
            {normalizedWorkflowResponse && (
              <div className="rounded-lg border border-border bg-background p-3">
                <div className="flex flex-wrap items-center gap-2">
                  {"status" in normalizedWorkflowResponse && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                      {String(normalizedWorkflowResponse.status)}
                    </span>
                  )}
                  {"runId" in normalizedWorkflowResponse && (
                    <span className="font-mono text-[11px] text-foreground">
                      workflow run: {String(normalizedWorkflowResponse.runId)}
                    </span>
                  )}
                </div>
                {"message" in normalizedWorkflowResponse && (
                  <p className="mt-2 text-muted-foreground">{String(normalizedWorkflowResponse.message)}</p>
                )}
              </div>
            )}
            <details className="rounded-lg border border-border bg-background p-3">
              <summary className="cursor-pointer text-[11px] text-muted-foreground">Raw response</summary>
              <pre className="mt-2 overflow-auto text-xs text-muted-foreground">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">Generated Videos</h3>
          <button
            type="button"
            onClick={fetchRuns}
            className="rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted"
          >
            {loadingRuns ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {runs.length === 0 ? (
          <p className="text-xs text-muted-foreground">No UGC videos yet.</p>
        ) : (
          <div className="space-y-4">
            {runs.map((run) => (
              <div key={run.id} className="rounded-xl border border-border p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{run.productName}</span>
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                    {run.status}
                  </span>
                  {run.language && (
                    <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                      {run.language}
                    </span>
                  )}
                </div>

                {run.error && (
                  <p className="mb-2 text-xs text-destructive">{run.error}</p>
                )}

                {Array.isArray(run.variants) && run.variants.length > 0 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {run.variants.map((variant, idx) => (
                      <div key={`${run.id}-${idx}`} className="rounded-lg border border-border p-2">
                        <p className="mb-2 text-[11px] text-muted-foreground">
                          Variant {variant.index ?? idx + 1}
                        </p>
                        {variant.videoUrl ? (
                          <video controls className="w-full rounded-md border border-border">
                            <source src={variant.videoUrl} />
                          </video>
                        ) : (
                          <p className="text-xs text-muted-foreground">Video URL unavailable</p>
                        )}
                        <div className="mt-2 flex flex-wrap gap-2">
                          {variant.videoUrl && (
                            <a
                              href={variant.videoUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-primary underline"
                            >
                              Open
                            </a>
                          )}
                          {variant.downloadUrl && (
                            <a
                              href={variant.downloadUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-primary underline"
                            >
                              Download
                            </a>
                          )}
                          {variant.extendedUrl && (
                            <a
                              href={variant.extendedUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-primary underline"
                            >
                              Extended
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Waiting for n8n callback...</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
