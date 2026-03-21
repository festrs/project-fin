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

let _cache: NewsItem[] | null = null;

export function useNews() {
  const [news, setNews] = useState<NewsItem[]>(_cache ?? []);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<{ news: NewsItem[] }>("/news")
      .then((res) => {
        _cache = res.data.news;
        setNews(_cache);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch news");
      })
      .finally(() => setLoading(false));
  }, []);

  return { news, loading, error };
}
