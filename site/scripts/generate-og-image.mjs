#!/usr/bin/env node
// sb-z8zk — Generate 1200x630 OG image for SynthBench social previews.
// Output: site/public/og-image.png
// Run: node scripts/generate-og-image.mjs (from site/)

import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outPath = path.resolve(__dirname, "..", "public", "og-image.png");
mkdirSync(path.dirname(outPath), { recursive: true });

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1e1b4b"/>
      <stop offset="1" stop-color="#312e81"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#6366f1"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <!-- decorative chart bars to evoke a benchmark/leaderboard -->
  <g opacity="0.18" transform="translate(720 380)">
    <rect x="0"   y="110" width="40" height="40"  rx="4" fill="#a5b4fc"/>
    <rect x="60"  y="80"  width="40" height="70"  rx="4" fill="#a5b4fc"/>
    <rect x="120" y="40"  width="40" height="110" rx="4" fill="#a5b4fc"/>
    <rect x="180" y="20"  width="40" height="130" rx="4" fill="#a5b4fc"/>
    <rect x="240" y="60"  width="40" height="90"  rx="4" fill="#a5b4fc"/>
    <rect x="300" y="0"   width="40" height="150" rx="4" fill="#a5b4fc"/>
    <rect x="360" y="30"  width="40" height="120" rx="4" fill="#a5b4fc"/>
  </g>
  <!-- logo mark -->
  <rect x="80" y="80" width="96" height="96" rx="16" fill="url(#accent)"/>
  <text x="128" y="148" text-anchor="middle" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="64" font-weight="800" fill="#ffffff">S</text>
  <!-- wordmark -->
  <text x="200" y="148" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="56" font-weight="800" fill="#ffffff">SynthBench</text>
  <!-- headline -->
  <text x="80" y="320" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="68" font-weight="800" fill="#ffffff">Open benchmark for</text>
  <text x="80" y="404" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="68" font-weight="800" fill="#a5b4fc">synthetic survey quality</text>
  <!-- subtitle -->
  <text x="80" y="478" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="30" font-weight="400" fill="#e0e7ff">Reproducible scoring of LLM-generated survey respondents</text>
  <!-- footer url -->
  <text x="80" y="560" font-family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif" font-size="26" font-weight="600" fill="#c7d2fe">synthbench.org</text>
</svg>`;

await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toFile(outPath);
console.log(`Wrote ${outPath}`);
