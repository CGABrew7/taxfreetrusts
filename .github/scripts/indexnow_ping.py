#!/usr/bin/env python3
"""Ping IndexNow for page URLs that changed in this deploy.

No-ops if the key file is not live yet, if there is no previous commit to
diff against, or if no mappable page URLs changed. Never submits a sitemap.
A failed IndexNow POST is logged and is not a job failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOST = os.environ["INDEXNOW_HOST"]
KEY = os.environ["INDEXNOW_KEY"]
KIND = os.environ.get("INDEXNOW_KIND", "static-html")
SLASH = os.environ.get("INDEXNOW_SLASH", "never")  # always | never | dir
PAGES_ROOT = os.environ.get("INDEXNOW_PAGES_ROOT", "src/pages").rstrip("/")
STATIC_ROOT = os.environ.get("INDEXNOW_STATIC_ROOT", "").rstrip("/")
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"

SKIP_PREFIXES = (
    "functions/",
    ".github/",
    "node_modules/",
    "docs/",
    "scripts/",
    "cron_prompts/",
    "research/",
    "drafts/",
    "test/",
    "tests/",
    "mcp/",
    "mcp-server/",
    "muse/",
    "qa/",
    "dev/",
    ".git/",
    "server/",
    "migrations/",
)

SKIP_NAMES = {
    "404.html",
    "404.astro",
    "robots.txt",
    "robots.txt.js",
    "sitemap.xml",
    "sitemap.xml.js",
    "sitemap.xml.ts",
    "llms.txt",
    "llms.txt.js",
    "rss.xml",
    "rss.xml.js",
    "sitemap[.]xml.ts",
}

SKIP_SUFFIXES = (
    ".css",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".json",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".map",
    ".toml",
    ".yml",
    ".yaml",
    ".lock",
    ".md",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def key_live() -> bool:
    try:
        req = urllib.request.Request(
            KEY_LOCATION, headers={"User-Agent": "HanokIndexNow/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace").strip()
            ctype = resp.headers.get("Content-Type", "")
            if body != KEY:
                log(f"key body mismatch ({len(body)} bytes, type={ctype})")
                return False
            return True
    except Exception as exc:
        log(f"key fetch failed: {exc}")
        return False


def wait_for_key() -> bool:
    for i in range(20):
        if key_live():
            log("key is live")
            return True
        log(f"waiting for key ({i + 1}/20)")
        time.sleep(30)
    return False


def git_lines(args: list[str]) -> list[str]:
    try:
        out = subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        log(f"git command failed: {exc.output}")
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_files() -> list[str] | None:
    if os.environ.get("INDEXNOW_DIFF_HEAD") == "1":
        files = git_lines(["git", "diff", "--name-only", "HEAD"])
        files += git_lines(["git", "ls-files", "--others", "--exclude-standard"])
        return sorted(set(files))
    before = os.environ.get("INDEXNOW_BEFORE") or os.environ.get("GITHUB_EVENT_BEFORE") or ""
    after = os.environ.get("INDEXNOW_AFTER") or os.environ.get("GITHUB_SHA") or "HEAD"
    if not before or set(before) == {"0"}:
        log("no previous commit to diff; no-op so we do not submit a full URL list")
        return None
    return git_lines(["git", "diff", "--name-only", f"{before}...{after}"])


def canon(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and SLASH == "always" and not path.endswith("/"):
        path += "/"
    if path != "/" and SLASH == "never":
        path = path.rstrip("/") or "/"
    return f"https://{HOST}{path}"


def strip_static_root(path: str) -> str | None:
    if STATIC_ROOT:
        prefix = STATIC_ROOT + "/"
        if path == STATIC_ROOT:
            return None
        if not path.startswith(prefix):
            return None
        return path[len(prefix) :]
    return path


def skip_static(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name in SKIP_NAMES or name.startswith(".") or name == f"{KEY}.txt":
        return True
    for prefix in SKIP_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return True
    return False


def map_html(rel: str) -> str | None:
    if not rel.endswith(".html"):
        return None
    name = rel.rsplit("/", 1)[-1]
    if name in SKIP_NAMES:
        return None
    if rel.endswith("/index.html") or rel == "index.html":
        parent = "" if rel == "index.html" else rel[: -len("index.html")]
        path = "/" + parent
        path = path.rstrip("/") or "/"
        if path != "/" and SLASH in ("always", "dir"):
            path += "/"
        return f"https://{HOST}{path}"
    path = "/" + rel[: -len(".html")]
    if SLASH == "always" and not path.endswith("/"):
        path += "/"
    return f"https://{HOST}{path}"


def map_astro(path: str) -> str | None:
    root = PAGES_ROOT + "/"
    if not path.startswith(root):
        return None
    rel = path[len(root) :]
    if "[" in rel or "]" in rel:
        return None
    name = rel.rsplit("/", 1)[-1]
    if name in SKIP_NAMES:
        return None
    if not any(rel.endswith(ext) for ext in (".astro", ".md", ".mdx", ".html")):
        return None
    for ext in (".astro", ".md", ".mdx", ".html"):
        if rel.endswith(ext):
            rel = rel[: -len(ext)]
            break
    if rel == "index" or rel.endswith("/index"):
        rel = rel[: -len("index")]
    path_url = "/" + rel
    path_url = path_url.rstrip("/") or "/"
    return canon(path_url)


def map_tanstack(path: str) -> str | None:
    if path.startswith("src/content/posts/") and path.endswith(".ts"):
        name = path.rsplit("/", 1)[-1][: -len(".ts")]
        if name in {"index", "types"} or "functions" in name:
            return None
        return canon(f"/blog/{name}")
    if not path.startswith("src/routes/") or not path.endswith((".tsx", ".ts")):
        return None
    rel = path[len("src/routes/") :]
    name = rel.rsplit("/", 1)[-1]
    if name.startswith("__") or "$" in rel or "[" in rel:
        return None
    if name in SKIP_NAMES:
        return None
    for ext in (".tsx", ".ts"):
        if rel.endswith(ext):
            rel = rel[: -len(ext)]
            break
    if rel == "index" or rel.endswith("/index"):
        rel = rel[: -len("index")]
    path_url = "/" + rel
    path_url = path_url.rstrip("/") or "/"
    return canon(path_url)


def map_witl_data(path: str) -> str | None:
    if path.startswith("data/digests/") and path.endswith(".json"):
        slug = path[len("data/digests/") : -len(".json")]
        if "/" in slug or not slug:
            return None
        return canon(f"/digest/{slug}")
    if path.startswith("data/top10/") and path.endswith(".json"):
        slug = path[len("data/top10/") : -len(".json")]
        if "/" in slug or not slug:
            return None
        return canon(f"/top-10/{slug}")
    # Index pages that re-render when the shared data files change.
    # Do not expand a data file into every model or launch URL.
    data_indexes = {
        "data/models.json": "/models/",
        "data/launches.json": "/launches/",
        "data/leaderboards.json": "/leaderboards/",
        "data/research.json": "/research/",
        "data/entities.json": "/",
        "data/news-archive.json": "/news/",
        "data/tools.json": "/",
        "data/status.json": "/",
    }
    if path in data_indexes:
        return canon(data_indexes[path])
    return None


def map_file(path: str) -> list[str]:
    urls: list[str] = []
    if KIND == "astro":
        u = map_astro(path)
        if u:
            urls.append(u)
        if HOST == "whatisthelatest.ai":
            u = map_witl_data(path)
            if u:
                urls.append(u)
        return urls
    if KIND == "tanstack":
        u = map_tanstack(path)
        if u:
            urls.append(u)
        return urls
    if KIND == "fe":
        # Pages are generated in build.mjs, so a script edit is not mapped
        # to the whole site. Only direct public HTML files are submitted.
        rel = strip_static_root(path) if STATIC_ROOT else path
        if rel and rel.startswith("public/") and rel.endswith(".html"):
            u = map_html(rel[len("public/") :])
            if u:
                urls.append(u)
        return urls
    # static-html
    rel = strip_static_root(path)
    if rel is None or skip_static(rel):
        return []
    u = map_html(rel)
    if u:
        urls.append(u)
    return urls


def post(urls: list[str]) -> None:
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls[:10000],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "HanokIndexNow/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            log(f"IndexNow response {resp.status} for {len(urls)} URLs")
    except Exception as exc:
        log(f"IndexNow post failed (non-fatal): {exc}")


def main() -> int:
    if not wait_for_key():
        log("key not live after about 10 minutes; no-op")
        return 0
    files = changed_files()
    if files is None:
        return 0
    urls: list[str] = []
    seen = set()
    for path in files:
        for url in map_file(path):
            if url not in seen:
                seen.add(url)
                urls.append(url)
    if not urls:
        log("no page URLs changed; no-op")
        return 0
    log("pinging {n} URLs: {sample}".format(n=len(urls), sample=", ".join(urls[:10])))
    post(urls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
