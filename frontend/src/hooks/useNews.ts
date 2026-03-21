import { useState, useEffect } from "react";
import api from "../services/api";

export interface NewsItem {
  id: number;
  category: string;
  headline: string;
  summary: string;
  url: string;
  source: string;
  datetime: number;
  image: string;
}

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

let _cache: NewsItem[] | null = null;
let _cacheTime = 0;

function isCacheFresh(): boolean {
  return _cache !== null && Date.now() - _cacheTime < CACHE_TTL_MS;
}

export function useNews() {
  const [news, setNews] = useState<NewsItem[]>(_cache ?? []);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isCacheFresh()) return;

    api
      .get<{ news: NewsItem[] }>("/news")
      .then((res) => {
        _cache = res.data.news;
        _cacheTime = Date.now();
        setNews(_cache);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch news");
      })
      .finally(() => setLoading(false));
  }, []);

  return { news, loading, error };
}
