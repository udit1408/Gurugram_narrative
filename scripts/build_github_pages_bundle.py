#!/usr/bin/env python3
from __future__ import annotations

import base64
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "OPEN_THIS_FINAL_DASHBOARD.html"
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"


MOBILE_CSS = """

/* Build-time mobile improvements for the GitHub Pages bundle */
.tabs {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}
.tabbtn,
.querybar button,
.button-row button,
.ward-toggle-grid button,
.anim-controls button {
  min-height: 42px;
}
.table-wrap {
  -webkit-overflow-scrolling: touch;
}
@media (max-width:980px) {
  .tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 14px;
  }
  .tabbtn {
    flex: 0 0 auto;
    white-space: nowrap;
  }
  .anim-controls,
  .anim-row,
  .ward-toggle-grid {
    grid-template-columns: 1fr;
  }
  .anim-row strong {
    justify-self: start;
  }
  .method-list {
    columns: 1;
  }
}
@media (max-width:760px) {
  header,
  .metrics,
  .tabs,
  .tab,
  footer {
    padding-left: 14px;
    padding-right: 14px;
  }
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .metric-card,
  .panel,
  .control-card,
  .mini,
  .spatial-anim-card {
    padding: 12px;
  }
  .metric-card strong {
    font-size: 16px;
  }
  h1 {
    font-size: 21px;
  }
  .sub,
  p,
  li {
    font-size: 13px;
  }
  .layer-frame {
    aspect-ratio: 1 / 1;
    min-height: 320px;
  }
  .large-layer-frame {
    aspect-ratio: 1 / 1.06;
    min-height: 360px;
  }
  .querybar,
  .grid3,
  .resultgrid {
    grid-template-columns: 1fr;
  }
  .depth-legend-head {
    display: block;
  }
  .depth-legend-head small {
    display: block;
    text-align: left;
    margin-top: 4px;
  }
  .depth-legend-labels {
    font-size: 9px;
  }
}
@media (max-width:520px) {
  .metrics {
    grid-template-columns: 1fr;
  }
  .layer-frame {
    min-height: 260px;
  }
  .large-layer-frame {
    min-height: 300px;
  }
}
"""


QUERY_HELPERS = """
let QUERY_DATA = null;
let queryDataPromise = null;
let queryNamesPopulated = false;
const QUERY_DATA_SRC = 'assets/dashboard-query-data.js';

function setQueryStatus(message) {
  const status = document.getElementById('queryStatus');
  if (status) status.textContent = message;
}

function populateQueryNames() {
  if (!QUERY_DATA || queryNamesPopulated) return;
  const names = document.getElementById('queryNames');
  if (!names) return;
  QUERY_DATA.gazetteer.forEach(g => {
    const opt = document.createElement('option');
    opt.value = g.name;
    names.appendChild(opt);
  });
  queryNamesPopulated = true;
}

function hydrateTabImages(scope) {
  const root = scope || document;
  const images = Array.from(root.querySelectorAll('img[data-src]'));
  if (!images.length) return Promise.resolve();
  return Promise.all(images.map(img => {
    if (img.dataset.loaded === '1') return Promise.resolve();
    return new Promise(resolve => {
      const finish = () => {
        img.dataset.loaded = '1';
        resolve();
      };
      img.addEventListener('load', finish, {once:true});
      img.addEventListener('error', finish, {once:true});
      img.src = img.dataset.src;
      img.decoding = 'async';
    });
  }));
}

function ensureQueryData() {
  if (QUERY_DATA) return Promise.resolve(QUERY_DATA);
  if (queryDataPromise) return queryDataPromise;
  setQueryStatus('Loading detailed query dataset...');
  queryDataPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = QUERY_DATA_SRC;
    script.onload = () => {
      QUERY_DATA = window.__DASHBOARD_QUERY_DATA__ || null;
      if (!QUERY_DATA) {
        reject(new Error('Query dataset loaded but no data object was found.'));
        return;
      }
      populateQueryNames();
      if (document.getElementById('queryStatus')?.textContent === 'Loading detailed query dataset...') {
        setQueryStatus('');
      }
      delete window.__DASHBOARD_QUERY_DATA__;
      resolve(QUERY_DATA);
    };
    script.onerror = () => reject(new Error(`Unable to load ${QUERY_DATA_SRC}`));
    document.head.appendChild(script);
  }).catch(err => {
    queryDataPromise = null;
    setQueryStatus('The detailed query dataset could not be loaded. Confirm that docs/assets is deployed with index.html.');
    throw err;
  });
  return queryDataPromise;
}
"""


def extract_query_data(script_text: str) -> tuple[str, str]:
    marker = "const QUERY_DATA = "
    split_marker = "const ANIMATION_DATA = "
    if marker not in script_text or split_marker not in script_text:
        raise RuntimeError("Could not find the inline query dataset block.")
    prefix, remainder = script_text.split(marker, 1)
    query_blob, suffix = remainder.split(split_marker, 1)
    query_json = query_blob.rsplit(";", 1)[0].strip()
    updated_script = prefix + QUERY_HELPERS + "const ANIMATION_DATA = " + suffix
    return query_json, updated_script


def rewrite_script(script_text: str) -> str:
    replacements = [
        (
            "function activateTab(tabId) {\n"
            "  document.querySelectorAll('.tabbtn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));\n"
            "  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.id === tabId));\n"
            "  if (tabId === 'layers') {\n"
            "    window.requestAnimationFrame(renderQueryMarkers);\n"
            "  }\n"
            "  if (tabId === 'wardmap') {\n"
            "    window.requestAnimationFrame(updateWardMap);\n"
            "  }\n"
            "}\n",
            """async function activateTab(tabId) {
  document.querySelectorAll('.tabbtn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.id === tabId));
  const tab = document.getElementById(tabId);
  const needsQueryData = tabId === 'layers' || tabId === 'wardmap' || tabId === 'query';
  const work = [hydrateTabImages(tab)];
  if (needsQueryData) work.push(ensureQueryData());
  try {
    await Promise.all(work);
  } catch (err) {
    console.error(err);
    return;
  }
  if (tabId === 'layers') {
    window.requestAnimationFrame(renderQueryMarkers);
  }
  if (tabId === 'wardmap') {
    window.requestAnimationFrame(updateWardMap);
  }
}
""",
        ),
        (
            "function applyWardCrop() {\n"
            "  const frame = document.getElementById('wardMapFrame');\n",
            "function applyWardCrop() {\n  if (!QUERY_DATA) return;\n  const frame = document.getElementById('wardMapFrame');\n",
        ),
        (
            "function wardCropTransformState() {\n"
            "  const img = imageRectForFrame('wardMapFrame');\n",
            "function wardCropTransformState() {\n  if (!QUERY_DATA) return null;\n  const img = imageRectForFrame('wardMapFrame');\n",
        ),
        (
            "function renderWardHover(event) {\n"
            "  const tip = document.getElementById('wardHoverTooltip');\n",
            "function renderWardHover(event) {\n  if (!QUERY_DATA) {\n    hideWardHoverTooltip();\n    return;\n  }\n  const tip = document.getElementById('wardHoverTooltip');\n",
        ),
        (
            "function parseQuery(text) {\n"
            "  const dms = parseDms(text);\n",
            "function parseQuery(text) {\n  if (!QUERY_DATA) return null;\n  const dms = parseDms(text);\n",
        ),
        (
            "function runQuery() {\n"
            "  const loc = parseQuery(document.getElementById('queryInput').value);\n",
            "async function runQuery() {\n  try {\n    await ensureQueryData();\n  } catch (err) {\n    console.error(err);\n    return;\n  }\n  const loc = parseQuery(document.getElementById('queryInput').value);\n",
        ),
        (
            "function activeNonBuilding(i) {\n"
            "  return Number(QUERY_DATA.active[i]) === 1 && Number(QUERY_DATA.building[i]) === 0;\n"
            "}\n",
            "function activeNonBuilding(i) {\n  if (!QUERY_DATA) return false;\n  return Number(QUERY_DATA.active[i]) === 1 && Number(QUERY_DATA.building[i]) === 0;\n}\n",
        ),
        (
            "function pixelToUtm(point) {\n"
            "  const e = QUERY_DATA.extent;\n",
            "function pixelToUtm(point) {\n  if (!QUERY_DATA) return null;\n  const e = QUERY_DATA.extent;\n",
        ),
        (
            "function utmToPixel(x, y) {\n"
            "  const img = currentImageRect();\n",
            "function utmToPixel(x, y) {\n  if (!QUERY_DATA) return null;\n  const img = currentImageRect();\n",
        ),
        (
            "function placeQueryRing(pixel, radiusM=150) {\n"
            "  const ring = document.getElementById('queryRing');\n",
            "function placeQueryRing(pixel, radiusM=150) {\n  if (!QUERY_DATA) return;\n  const ring = document.getElementById('queryRing');\n",
        ),
        (
            "function renderQueryMarkers() {\n"
            "  if (!LAST_QUERY_MARKERS) {\n",
            "function renderQueryMarkers() {\n  if (!QUERY_DATA) {\n    hideQueryMarkers();\n    return;\n  }\n  if (!LAST_QUERY_MARKERS) {\n",
        ),
        (
            "  drawBtn.addEventListener('click', () => {\n"
            "    drawMode = true;\n"
            "    frame.classList.add('draw-mode');\n"
            "    document.getElementById('aoiStatus').textContent = 'Draw mode active: drag a rectangle on the map.';\n"
            "  });\n",
            """  drawBtn.addEventListener('click', async () => {
    try {
      await ensureQueryData();
    } catch (err) {
      console.error(err);
      return;
    }
    drawMode = true;
    frame.classList.add('draw-mode');
    document.getElementById('aoiStatus').textContent = 'Draw mode active: drag a rectangle on the map.';
  });
""",
        ),
        (
            "  frame.addEventListener('pointerup', e => {\n"
            "    if (!drawing || !start) return;\n",
            "  frame.addEventListener('pointerup', e => {\n    if (!QUERY_DATA || !drawing || !start) return;\n",
        ),
        (
            "document.getElementById('queryExample').addEventListener('click', () => {\n"
            "  document.getElementById('queryInput').value = 'Galleria Market';\n"
            "  runQuery();\n"
            "});\n",
            "document.getElementById('queryExample').addEventListener('click', async () => {\n  document.getElementById('queryInput').value = 'Galleria Market';\n  await runQuery();\n});\n",
        ),
        (
            "if (initialQuery) {\n"
            "  document.getElementById('queryInput').value = initialQuery;\n"
            "  window.requestAnimationFrame(runQuery);\n"
            "}\n",
            "if (initialQuery) {\n  document.getElementById('queryInput').value = initialQuery;\n  window.requestAnimationFrame(() => { void runQuery(); });\n}\n",
        ),
    ]
    for old, new in replacements:
        if old not in script_text:
            raise RuntimeError(f"Expected script fragment not found:\n{old[:120]}")
        script_text = script_text.replace(old, new, 1)
    return script_text


def write_image_assets(html_text: str) -> str:
    image_index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal image_index
        image_index += 1
        before = match.group(1)
        mime = match.group(2)
        payload = match.group(3)
        after = match.group(4)
        extension = "png" if mime == "png" else mime.replace("jpeg", "jpg")
        filename = f"dashboard-image-{image_index:03d}.{extension}"
        (ASSETS / filename).write_bytes(base64.b64decode(payload))
        return f'<img{before}data-src="assets/{filename}" loading="lazy" decoding="async"{after}>'

    pattern = re.compile(r'<img([^>]*?)src="data:image/([^;]+);base64,([^"]+)"([^>]*)>', re.S)
    updated_html = pattern.sub(replace, html_text)
    if image_index == 0:
        raise RuntimeError("No inline images were found to extract.")
    return updated_html


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source dashboard: {SOURCE}")

    DOCS.mkdir(exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    html = SOURCE.read_text()
    html = html.replace("</style>", MOBILE_CSS + "\n</style>", 1)
    html = write_image_assets(html)

    script_match = re.search(r"<script>(.*)</script>", html, re.S)
    if not script_match:
        raise RuntimeError("No script block found in dashboard HTML.")

    query_json, rewritten_script = extract_query_data(script_match.group(1))
    rewritten_script = rewrite_script(rewritten_script)
    html = html[: script_match.start(1)] + rewritten_script + html[script_match.end(1) :]

    (ASSETS / "dashboard-query-data.js").write_text(
        "window.__DASHBOARD_QUERY_DATA__ = " + query_json + ";\n"
    )
    (DOCS / "index.html").write_text(html)
    (DOCS / ".nojekyll").write_text("")

    print(f"Wrote {DOCS / 'index.html'}")
    print(f"Wrote {(ASSETS / 'dashboard-query-data.js')}")
    print(f"Extracted {len(list(ASSETS.glob('dashboard-image-*')))} image assets into {ASSETS}")


if __name__ == "__main__":
    main()
