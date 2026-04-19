import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { RunIndex } from "@/types/runs";
import type { APIRoute } from "astro";

// sb-d4mw — static sitemap for SEO + Google Search Console. Emitted as
// `/sitemap.xml` at build time. Lists public static pages plus every run
// detail URL from `public/data/runs-index.json` (matches the getStaticPaths
// source used by `src/pages/run/[id].astro`, so the two stay in lockstep).
//
// Non-indexable auth/account/upload pages are intentionally excluded.
// `robots.txt` points here so crawlers can discover the feed.

const STATIC_PATHS = [
  "",
  "compare/",
  "explore/",
  "findings/",
  "leaderboard/",
  "methodology/",
  "submit/",
] as const;

const xmlEscape = (s: string): string =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

// Mirror the URL encoding used by run/[id].astro so the sitemap references
// the same on-disk filenames the static host will serve.
const encodePathSegment = (s: string): string =>
  s.replace(/ /g, "%20").replace(/#/g, "%23").replace(/\?/g, "%3F");

function loadRunIds(): string[] {
  const indexPath = resolve("public/data/runs-index.json");
  if (!existsSync(indexPath)) return [];
  const index = JSON.parse(readFileSync(indexPath, "utf-8")) as RunIndex;
  return index.runs.map((r) => r.run_id);
}

export const GET: APIRoute = ({ site }) => {
  if (!site) {
    throw new Error("sitemap.xml requires `site` in astro.config");
  }
  const origin = new URL(site).origin;
  const base = (import.meta.env.BASE_URL || "/").replace(/\/?$/, "/");
  const urlFor = (path: string) => `${origin}${base}${path}`;

  const runIds = loadRunIds();
  const indexJson = resolve("public/data/runs-index.json");
  // Use the index's generated_at (if readable) as lastmod for run pages so
  // the feed only re-advertises freshness when the catalog actually changes.
  let runLastmod: string | null = null;
  if (existsSync(indexJson)) {
    try {
      const parsed = JSON.parse(readFileSync(indexJson, "utf-8")) as RunIndex;
      runLastmod = parsed.generated_at ?? null;
    } catch {
      runLastmod = null;
    }
  }

  const urls: string[] = [];
  for (const path of STATIC_PATHS) {
    urls.push(`  <url><loc>${xmlEscape(urlFor(path))}</loc></url>`);
  }
  for (const id of runIds) {
    const loc = urlFor(`run/${encodePathSegment(id)}/`);
    const lastmodTag = runLastmod ? `<lastmod>${xmlEscape(runLastmod)}</lastmod>` : "";
    urls.push(`  <url><loc>${xmlEscape(loc)}</loc>${lastmodTag}</url>`);
  }

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join("\n")}
</urlset>
`;

  return new Response(body, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
    },
  });
};
