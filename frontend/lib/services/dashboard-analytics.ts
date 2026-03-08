"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { clearAuthToken, getAuthToken } from "@/lib/auth";

type SectionName =
  | "dashboard"
  | "overview"
  | "visibility"
  | "competitors"
  | "prompts"
  | "alerts";

export interface ApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

// ─── Module-level cache ───────────────────────────────────────────────────────
// Lives outside React — survives tab navigation / component unmounts.
// Key: section name. Value: { data, fetchedAt }
const sectionCache = new Map<string, { data: unknown; fetchedAt: number }>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes — re-fetch in background after this

function getCached<T>(section: string): T | null {
  const entry = sectionCache.get(section);
  if (!entry) return null;
  return entry.data as T;
}

function isStale(section: string): boolean {
  const entry = sectionCache.get(section);
  if (!entry) return true;
  return Date.now() - entry.fetchedAt > CACHE_TTL_MS;
}

function setCached(section: string, data: unknown): void {
  sectionCache.set(section, { data, fetchedAt: Date.now() });
}

// ─────────────────────────────────────────────────────────────────────────────

async function requestSection<T>(section: SectionName): Promise<T> {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Authentication required");
  }

  const baseUrl = process.env.NEXT_PUBLIC_BRAND_MONITOR_URL || "http://localhost:4001";
  const response = await fetch(`${baseUrl}/api/brand-monitor/analytics/${section}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await response.json().catch(() => ({}));
  if (response.status === 401) {
    clearAuthToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!response.ok) {
    const message =
      json?.error?.message ||
      json?.error ||
      `Failed to load ${section} analytics`;
    throw new Error(message);
  }
  return json as T;
}

export function useAnalyticsSection<T>(section: SectionName): ApiResult<T> {
  // Hydrate immediately from cache so there is no "zero flash" on tab switch
  const cached = getCached<T>(section);
  const [data, setData] = useState<T | null>(cached);
  const [loading, setLoading] = useState(cached === null); // only show spinner if nothing cached
  const [error, setError] = useState<string | null>(null);
  const isMounted = useRef(true);

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const result = await requestSection<T>(section);
      setCached(section, result);
      if (isMounted.current) setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to load ${section} analytics`;
      // Only surface the error if we have no cached data to show
      if (isMounted.current && getCached(section) === null) setError(message);
    } finally {
      if (isMounted.current && !silent) setLoading(false);
    }
  }, [section]);

  useEffect(() => {
    isMounted.current = true;
    if (isStale(section)) {
      // If cache is missing → show spinner.  If cache exists but stale → refresh silently.
      fetchData(cached !== null);
    }
    return () => {
      isMounted.current = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  return useMemo(
    () => ({
      data,
      loading,
      error,
      refresh: () => fetchData(false),
    }),
    [data, loading, error, fetchData],
  );
}
