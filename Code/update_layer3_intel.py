from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
WATCHLIST_PATH = DATA_DIR / "layer3_watchlist.json"
INBOX_PATH = DATA_DIR / "layer3_source_inbox_2026.json"
CLAIMS_PATH = DATA_DIR / "layer3_extracted_claims_2026.json"
REGISTRY_PATH = DATA_DIR / "team_availability_2026.json"

DEFAULT_MODEL = os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

PRIORITY_SCORE = {
    "official": 5,
    "coach_quote": 4,
    "team_media": 4,
    "major_media": 3,
    "beat_report": 2,
    "speculative": 1,
    "manual": 3,
}

STATUS_VALUES = {
    "available",
    "doubtful",
    "ruled_out",
    "managed",
    "overseas_unavailable",
    "unknown",
}

TEAM_NAMES = {
    "RR": ["rajasthan royals", "royals"],
    "CSK": ["chennai super kings", "super kings", "csk"],
    "KKR": ["kolkata knight riders", "knight riders", "kkr"],
    "MI": ["mumbai indians", "mi"],
    "RCB": ["royal challengers bengaluru", "royal challengers bangalore", "rcb", "challengers"],
    "LSG": ["lucknow super giants", "lsg", "super giants"],
    "DC": ["delhi capitals", "dc", "capitals"],
    "SRH": ["sunrisers hyderabad", "srh", "sunrisers"],
    "GT": ["gujarat titans", "gt", "titans"],
    "PBKS": ["punjab kings", "pbks", "kings"],
}

PLAYER_HINTS = {
    "RR": ["yashasvi jaiswal", "riyan parag", "dhruv jurel", "ravindra jadeja", "jofra archer", "shimron hetmyer", "sandeep sharma", "ravi bishnoi"],
    "CSK": ["ms dhoni", "ruturaj gaikwad", "sanju samson", "shivam dube", "noor ahmad", "rahul chahar", "nathan ellis"],
    "KKR": ["ajinkya rahane", "sunil narine", "rinku singh", "matheesha pathirana", "cameron green"],
    "MI": ["rohit sharma", "suryakumar yadav", "hardik pandya", "jasprit bumrah", "trent boult", "tilak verma"],
    "RCB": ["virat kohli", "rajat patidar", "phil salt", "jitesh sharma", "josh hazlewood", "bhuvneshwar kumar"],
    "LSG": ["rishabh pant", "nicholas pooran", "mitchell marsh", "mohammed shami", "mayank yadav", "wanindu hasaranga"],
    "DC": ["kl rahul", "axar patel", "tristan stubbs", "mitchell starc", "kuldeep yadav", "nitish rana"],
    "SRH": ["travis head", "abhishek sharma", "ishan kishan", "heinrich klaasen", "pat cummins", "liam livingstone"],
    "GT": ["shubman gill", "sai sudharsan", "jos buttler", "rashid khan", "mohammed siraj", "prasidh krishna"],
    "PBKS": ["shreyas iyer", "prabhsimran singh", "marco jansen", "arshdeep singh", "yuzvendra chahal", "marcus stoinis"],
}

AVAILABILITY_TERMS = [
    "injury", "injured", "available", "availability", "unavailable", "miss", "missing",
    "ruled out", "doubtful", "fit", "fitness", "recovery", "rehab", "replacement",
    "squad", "playing xi", "expected xi", "selection", "rested", "workload", "managed",
    "overseas", "returns", "returning", "captain", "training", "practice",
]

ARTICLE_HINTS = [
    "injury", "injured", "miss", "missing", "replacement", "replaces", "rejoined",
    "returns", "return", "ruled-out", "ruled-out", "ruled", "available", "availability",
    "doubt", "fitness", "training", "squad", "match preview", "preview", "opener",
]

VERBOSE = False
JUNK_TITLE_TERMS = [
    "csktv", "squad", "schedule", "fixtures", "points table", "points-table",
    "live cricket scores", "need ", "won", "preview", "tickets", "shop",
    "gallery", "photos", "videos", "starting 11", "wpl", "women",
]
STRONG_AVAILABILITY_TERMS = [
    "injury", "injured", "miss", "missing", "ruled out", "replacement",
    "replaces", "replaced", "returns", "return", "fit", "fitness",
    "rejoined", "availability", "unavailable", "training", "side strain",
    "hamstring", "recover", "doubtful", "managed",
]


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def log_debug(message: str) -> None:
    if VERBOSE:
        print(f"[Layer3][debug] {message}")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def strip_html(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return unescape(raw).strip()


def normalize_text(raw: str) -> str:
    return re.sub(r"\s+", " ", unescape(str(raw or "")).lower()).strip()


def source_scope_keywords(source: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for team_code in source.get("team_scope", []) or []:
        keywords.extend(TEAM_NAMES.get(str(team_code).upper(), []))
        keywords.extend(PLAYER_HINTS.get(str(team_code).upper(), []))
    keywords.extend(AVAILABILITY_TERMS)
    return sorted({keyword for keyword in keywords if keyword})


def relevance_score(text: str, source: dict[str, Any]) -> int:
    lowered = normalize_text(text)
    score = 0
    for keyword in source_scope_keywords(source):
        if keyword in lowered:
            score += 1
    return score


def has_strong_availability_signal(text: str) -> bool:
    lowered = normalize_text(text)
    return any(term in lowered for term in STRONG_AVAILABILITY_TERMS)


def looks_like_junk_item(title: str, raw_text: str = "") -> bool:
    combined = normalize_text(f"{title} {raw_text}")
    if any(term in combined for term in JUNK_TITLE_TERMS):
        if not has_strong_availability_signal(combined):
            return True
    return False


def keep_relevant_text(raw_text: str, source: dict[str, Any]) -> str:
    cleaned = strip_html(raw_text)
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[\.\!\?])\s+", cleaned)
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        trimmed = sentence.strip()
        if len(trimmed) < 40:
            continue
        score = relevance_score(trimmed, source)
        if score > 0:
            scored.append((score, trimmed))
    if not scored:
        return cleaned[:12000]
    scored.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    selected: list[str] = []
    total_chars = 0
    for _, sentence in scored:
        if sentence in selected:
            continue
        selected.append(sentence)
        total_chars += len(sentence) + 1
        if total_chars >= 9000 or len(selected) >= 40:
            break
    return " ".join(selected)[:12000]


def normalize_replacement_candidates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        raw = re.split(r",|/|;| and ", value)
    else:
        raw = [value]
    candidates: list[str] = []
    for item in raw:
        name = str(item).strip()
        if not name:
            continue
        if len(name) == 1:
            continue
        if name not in candidates:
            candidates.append(name)
    return candidates


def fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36 CreaseIQ-Layer3-Intel/1.0"
            ),
            "Accept": "text/html,application/xml,application/rss+xml,application/atom+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.google.com/",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def looks_like_rss(text: str) -> bool:
    prefix = text.lstrip()[:200].lower()
    return prefix.startswith("<?xml") or "<rss" in prefix or "<feed" in prefix


def parse_rss_items(source: dict[str, Any], raw_text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    root = ET.fromstring(raw_text)
    for item in root.findall(".//item")[:20]:
      title = (item.findtext("title") or "").strip()
      link = (item.findtext("link") or "").strip()
      description = (item.findtext("description") or "").strip()
      pub_date = (item.findtext("pubDate") or "").strip()
      if not title and not description:
          continue
      items.append(
          {
              "title": title or source["name"],
              "url": link or source["url"],
              "published_at": pub_date,
              "raw_text": keep_relevant_text(description, source),
          }
      )
    return items


def parse_web_item(source: dict[str, Any], raw_text: str) -> list[dict[str, Any]]:
    title_match = re.search(r"<title>(.*?)</title>", raw_text, flags=re.IGNORECASE | re.DOTALL)
    title = strip_html(title_match.group(1)) if title_match else source["name"]
    meta_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    extracted_meta = []
    for block in meta_blocks[:8]:
        try:
            payload = json.loads(block.strip())
        except Exception:
            continue
        queue = payload if isinstance(payload, list) else [payload]
        for item in queue:
            if not isinstance(item, dict):
                continue
            for key in ("headline", "description", "articleBody", "name"):
                value = item.get(key)
                if isinstance(value, str) and len(value.strip()) > 20:
                    extracted_meta.append(value.strip())
    combined = " ".join(extracted_meta) + " " + raw_text
    body = keep_relevant_text(combined, source)
    return [
        {
            "title": title,
            "url": source["url"],
            "published_at": "",
            "raw_text": body,
        }
    ]


def parse_story_date(text: str) -> str:
    for pattern in [
        r"\b(\d{1,2}\s+[A-Za-z]{3,9},\s+\d{4})\b",
        r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def story_items_from_text(source: dict[str, Any], raw_text: str) -> list[dict[str, Any]]:
    cleaned = strip_html(raw_text)
    items: list[dict[str, Any]] = []

    if source["source_id"] == "ipl_official_news":
        pattern = re.compile(
            r"Article\s+(.*?)\s+(\d{1,2}\s+[A-Za-z]{3},\s+\d{4}).{0,120}?Read More",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(cleaned):
            title = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
            published_at = match.group(2).strip()
            snippet = title
            if relevance_score(snippet, source) > 0:
                items.append({"title": title, "url": source["url"], "published_at": published_at, "raw_text": snippet})

    elif source["source_id"] in {"rr_official_site", "kkr_official_site", "mi_official_site", "rcb_official_site", "lsg_official_site", "dc_official_site", "pbks_official_site", "gt_official_site"}:
        pattern = re.compile(
            r"([A-Z0-9][^.:\n]{18,220}?)\s+(\d{1,2}\s+[A-Za-z]{3},\s+\d{4})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(cleaned):
            title = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
            published_at = match.group(2).strip()
            if title.lower().startswith(("home", "news", "download", "load more", "share")):
                continue
            if relevance_score(title, source) > 0:
                items.append({"title": title, "url": source["url"], "published_at": published_at, "raw_text": title})

    elif source["source_id"] == "cricbuzz_latest_news":
        pattern = re.compile(
            r"IPL 2026\s+([^\.]{12,220}?)\s+([A-Z][^\.]{20,320})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(cleaned):
            title = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
            body = re.sub(r"\s+", " ", match.group(2)).strip()
            combined = f"{title}. {body}"
            if relevance_score(combined, source) > 0:
                items.append({"title": title, "url": source["url"], "published_at": "", "raw_text": combined})

    elif source["source_id"] == "csk_official_site":
        pattern = re.compile(
            r"(Spencer Johnson joins CSK for TATA IPL 2026|MS Dhoni[^\.]{0,180}|Nathan Ellis[^\.]{0,180}|Sanju Samson[^\.]{0,180})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(cleaned):
            title = re.sub(r"\s+", " ", match.group(1)).strip(" -|")
            if relevance_score(title, source) > 0:
                items.append({"title": title, "url": source["url"], "published_at": parse_story_date(cleaned), "raw_text": title})

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = normalize_text(item["title"])
        if len(key) < 10 or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    log_debug(f"{source['source_id']} story-item adapter produced {len(deduped)} candidate snippets")
    return deduped[: max(int(source.get("max_articles", 4)) * 2, 6)]


def candidate_article_links(source: dict[str, Any], raw_text: str) -> list[dict[str, str]]:
    base_url = str(source.get("url") or "").strip()
    base_host = urlparse(base_url).netloc.lower()
    seen: set[str] = set()
    candidates: list[dict[str, str]] = []

    def add_candidate(url: str, title: str = "") -> None:
        absolute = urljoin(base_url, url.strip())
        parsed = urlparse(absolute)
        if not parsed.scheme.startswith("http"):
            return
        if parsed.netloc.lower() != base_host:
            return
        cleaned = absolute.split("#", 1)[0]
        lowered = cleaned.lower()
        if cleaned in seen:
            return
        if any(token in lowered for token in ["/login", "/signup", "/shop", "/tickets", "/photos", "/videos", "/gallery", "/stats", "/fixtures", "/points-table", "/squad"]):
            return
        title_text = strip_html(title)
        if looks_like_junk_item(title_text, cleaned):
            return
        score = relevance_score(f"{title_text} {cleaned}", source)
        score += sum(1 for hint in ARTICLE_HINTS if hint in f"{title_text} {cleaned}".lower())
        if score <= 0:
            return
        seen.add(cleaned)
        candidates.append({"url": cleaned, "title": title_text, "score": str(score)})

    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_text, flags=re.IGNORECASE | re.DOTALL):
        href, title = match.group(1), match.group(2)
        add_candidate(href, title)

    for block in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_text, flags=re.IGNORECASE | re.DOTALL):
        try:
            payload = json.loads(block.strip())
        except Exception:
            continue
        queue = payload if isinstance(payload, list) else [payload]
        for item in queue:
            if isinstance(item, dict):
                possible = []
                for key in ("url", "@id", "mainEntityOfPage"):
                    value = item.get(key)
                    if isinstance(value, str):
                        possible.append(value)
                    elif isinstance(value, dict) and isinstance(value.get("@id"), str):
                        possible.append(value["@id"])
                title = str(item.get("headline") or item.get("name") or "")
                for url in possible:
                    add_candidate(url, title)

    candidates.sort(key=lambda row: int(row["score"]), reverse=True)
    max_articles = int(source.get("max_articles", 4))
    log_debug(f"{source['source_id']} discovered {len(candidates[:max_articles])} article links")
    return candidates[:max_articles]


def parse_article_date(raw_text: str) -> str:
    for pattern in [
        r"\b(\d{1,2}\s+[A-Za-z]{3,9},\s+\d{4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]:
        match = re.search(pattern, raw_text)
        if match:
            return match.group(1)
    return ""


def parse_web_items(source: dict[str, Any], raw_text: str) -> list[dict[str, Any]]:
    items = parse_web_item(source, raw_text)
    for row in story_items_from_text(source, raw_text):
        items.append(row)
    for link in candidate_article_links(source, raw_text):
        try:
            article_raw = fetch_url(link["url"])
        except (HTTPError, URLError):
            log_debug(f"{source['source_id']} could not fetch article {link['url']}")
            continue
        except Exception:
            continue
        article_rows = parse_web_item({**source, "url": link["url"], "name": link["title"] or source["name"]}, article_raw)
        if not article_rows:
            continue
        article = article_rows[0]
        article["title"] = link["title"] or article["title"]
        article["published_at"] = parse_article_date(article_raw) or article.get("published_at", "")
        items.append(article)
    log_debug(f"{source['source_id']} total parsed web items: {len(items)}")
    return items


def groq_backoff_seconds(attempt: int) -> float:
    return 2.0 * (attempt + 1)


def source_item_id(source_id: str, url: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{source_id}_{title}_{urlparse(url).path}".lower()).strip("_")
    return slug[:120]


def team_scope_text(source: dict[str, Any]) -> list[str]:
    return [str(team).upper() for team in source.get("team_scope", [])]


def parse_team_filter(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {
        token.strip().upper()
        for token in str(raw).split(",")
        if token.strip()
    }


def source_matches_team_filter(source: dict[str, Any], team_filter: set[str]) -> bool:
    if not team_filter:
        return True
    source_scope = {str(team).upper() for team in source.get("team_scope", []) or []}
    return bool(source_scope & team_filter)


def inbox_matches_team_filter(item: dict[str, Any], team_filter: set[str]) -> bool:
    if not team_filter:
        return True
    item_scope = {str(team).upper() for team in item.get("team_scope", []) or []}
    team = str(item.get("team") or "").upper().strip()
    return bool(item_scope & team_filter) or (team in team_filter)


def ingest_sources(team_filter: set[str] | None = None) -> list[dict[str, Any]]:
    watchlist = load_json(WATCHLIST_PATH, [])
    inbox = load_json(INBOX_PATH, [])
    existing_ids = {item["source_item_id"] for item in inbox}
    new_items: list[dict[str, Any]] = []
    team_filter = team_filter or set()

    for source in watchlist:
        if not source.get("enabled"):
            continue
        if source.get("source_type") == "manual":
            continue
        if not source_matches_team_filter(source, team_filter):
            log_debug(f"{source['source_id']} skipped by team filter")
            continue
        url = str(source.get("url") or "").strip()
        if not url:
            continue

        try:
            raw_text = fetch_url(url)
        except (HTTPError, URLError) as exc:
            if not source.get("allow_403"):
                print(f"[Layer3] fetch failed for {source['source_id']}: {exc}")
            else:
                print(f"[Layer3] fetch blocked for {source['source_id']}: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"[Layer3] unexpected fetch failure for {source['source_id']}: {exc}")
            continue

        parsed_items = parse_rss_items(source, raw_text) if looks_like_rss(raw_text) else parse_web_items(source, raw_text)
        for row in parsed_items:
            if not row["raw_text"] or relevance_score(f"{row['title']} {row['raw_text']}", source) == 0:
                log_debug(f"{source['source_id']} skipped low-relevance item: {row.get('title','')[:90]}")
                continue
            item_id = source_item_id(source["source_id"], row["url"], row["title"])
            if item_id in existing_ids:
                log_debug(f"{source['source_id']} skipped duplicate item: {row['title'][:90]}")
                continue
            entry = {
                "source_item_id": item_id,
                "source_id": source["source_id"],
                "source_name": source["name"],
                "source_type": source["source_type"],
                "priority": source.get("priority", "major_media"),
                "team_scope": team_scope_text(source),
                "title": row["title"],
                "url": row["url"],
                "published_at": row["published_at"],
                "fetched_at": utc_now_iso(),
                "raw_text": row["raw_text"],
                "status": "unprocessed",
            }
            inbox.append(entry)
            new_items.append(entry)
            existing_ids.add(item_id)
            log_debug(f"{source['source_id']} added item: {row['title'][:110]}")

    save_json(INBOX_PATH, inbox)
    return new_items


def build_extraction_prompt(source_item: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You are extracting cricket player availability intelligence from a source item for an IPL analytics product. "
        "Return only JSON. Extract only explicit or strongly implied availability/selection information. "
        "Do not invent injuries or selection calls. Use these status values only: "
        "available, doubtful, ruled_out, managed, overseas_unavailable, unknown. "
        "Use these confidence values only: official, coach_quote, team_media, major_media, beat_report, speculative. "
        "Return a JSON array. Each row must contain: player, team, status, confidence, selection_probability, "
        "expected_absence_window, replacement_candidates, note."
    )
    user = json.dumps(
        {
            "source_name": source_item["source_name"],
            "priority": source_item["priority"],
            "team_scope": source_item["team_scope"],
            "title": source_item["title"],
            "published_at": source_item["published_at"],
            "url": source_item["url"],
            "raw_text": source_item["raw_text"][:9000],
        },
        ensure_ascii=False,
    )
    return system, user


def groq_extract_claims(source_item: dict[str, Any]) -> list[dict[str, Any]]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system_prompt, user_content = build_extraction_prompt(source_item)
    body = {
        "model": DEFAULT_MODEL,
        "max_tokens": 1400,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    last_error: Exception | None = None
    for attempt in range(3):
        request = Request(
            GROQ_API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": "CreaseIQ-Layer3-Intel/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload_raw = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < 2:
                wait_seconds = groq_backoff_seconds(attempt)
                log_debug(f"Groq 429 for {source_item['source_item_id']} · retrying in {wait_seconds:.1f}s")
                time.sleep(wait_seconds)
                continue
            raise
    else:
        raise last_error or RuntimeError("Groq request failed")
    content = payload_raw["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0].strip()
    rows = json.loads(content)
    if not isinstance(rows, list):
        raise ValueError("Groq extraction did not return a JSON array")
    return rows


def extract_claims(limit: int | None = None, team_filter: set[str] | None = None) -> list[dict[str, Any]]:
    inbox = load_json(INBOX_PATH, [])
    claims = load_json(CLAIMS_PATH, [])
    extracted: list[dict[str, Any]] = []
    team_filter = team_filter or set()

    pending = [
        item for item in inbox
        if item.get("status") != "processed" and inbox_matches_team_filter(item, team_filter)
    ]
    pending = [
        item for item in pending
        if not looks_like_junk_item(item.get("title", ""), item.get("raw_text", ""))
        and (has_strong_availability_signal(f"{item.get('title','')} {item.get('raw_text','')}") or "official" in str(item.get("priority", "")))
    ]
    pending.sort(
        key=lambda item: (
            has_strong_availability_signal(f"{item.get('title','')} {item.get('raw_text','')}"),
            PRIORITY_SCORE.get(str(item.get("priority") or ""), 0),
            relevance_score(f"{item.get('title','')} {item.get('raw_text','')}", {"team_scope": item.get("team_scope", [])}),
        ),
        reverse=True,
    )
    if limit is not None:
        pending = pending[:limit]

    for item in pending:
        if not GROQ_API_KEY:
            item["status"] = "pending_groq"
            continue
        try:
            rows = groq_extract_claims(item)
        except Exception as exc:  # noqa: BLE001
            item["status"] = "extract_failed"
            item["extract_error"] = str(exc)
            log_debug(f"extract failed for {item['source_item_id']}: {exc}")
            continue

        for idx, row in enumerate(rows):
            claim = {
                "claim_id": f"{item['source_item_id']}_claim_{idx + 1}",
                "source_item_id": item["source_item_id"],
                "source_id": item["source_id"],
                "source_name": item["source_name"],
                "priority": item["priority"],
                "player": str(row.get("player") or "").strip(),
                "team": str(row.get("team") or "").strip().upper(),
                "status": str(row.get("status") or "unknown").strip(),
                "confidence": str(row.get("confidence") or item["priority"]).strip(),
                "selection_probability": float(row.get("selection_probability") or 0),
                "expected_absence_window": row.get("expected_absence_window"),
                "replacement_candidates": normalize_replacement_candidates(row.get("replacement_candidates")),
                "note": str(row.get("note") or "").strip(),
                "source_date": item.get("published_at") or item.get("fetched_at"),
                "extracted_at": utc_now_iso(),
            }
            if claim["status"] not in STATUS_VALUES:
                claim["status"] = "unknown"
            if claim["confidence"] not in PRIORITY_SCORE:
                claim["confidence"] = item["priority"]
            claim["selection_probability"] = max(0.0, min(1.0, claim["selection_probability"]))
            if claim["player"]:
                claims.append(claim)
                extracted.append(claim)
                log_debug(f"claim extracted: {claim['team']} · {claim['player']} · {claim['status']}")
        item["status"] = "processed"
        time.sleep(1.0)

    save_json(INBOX_PATH, inbox)
    save_json(CLAIMS_PATH, claims)
    return extracted


def resolve_registry() -> list[dict[str, Any]]:
    claims = load_json(CLAIMS_PATH, [])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        player = str(claim.get("player") or "").strip()
        team = str(claim.get("team") or "").strip().upper()
        if not player or not team:
            continue
        grouped[(player, team)].append(claim)

    resolved: list[dict[str, Any]] = []
    for (player, team), rows in grouped.items():
        rows.sort(
            key=lambda row: (
                PRIORITY_SCORE.get(str(row.get("confidence") or row.get("priority")), 0),
                str(row.get("source_date") or ""),
            ),
            reverse=True,
        )
        best = rows[0]
        replacement_candidates: list[str] = []
        for row in rows:
            for candidate in normalize_replacement_candidates(row.get("replacement_candidates")):
                name = str(candidate).strip()
                if name and name not in replacement_candidates:
                    replacement_candidates.append(name)

        resolved.append(
            {
                "player": player,
                "team": team,
                "status": best["status"] if best["status"] in STATUS_VALUES else "unknown",
                "confidence": best.get("confidence") or best.get("priority") or "major_media",
                "selection_probability": float(best.get("selection_probability") or 0),
                "best_source": best.get("source_name", ""),
                "source_date": best.get("source_date", ""),
                "expected_absence_window": best.get("expected_absence_window"),
                "replacement_candidates": replacement_candidates,
                "note": best.get("note", ""),
            }
        )

    resolved.sort(key=lambda row: (row["team"], row["player"]))
    save_json(REGISTRY_PATH, resolved)
    return resolved


def print_summary(new_items: list[dict[str, Any]], extracted: list[dict[str, Any]], resolved: list[dict[str, Any]]) -> None:
    print(f"[Layer3] new source items: {len(new_items)}")
    print(f"[Layer3] extracted claims: {len(extracted)}")
    print(f"[Layer3] registry rows: {len(resolved)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Layer 3 availability intelligence for CreaseIQ.")
    parser.add_argument("--ingest-only", action="store_true", help="Fetch sources into inbox only.")
    parser.add_argument("--extract-only", action="store_true", help="Run Groq extraction on inbox only.")
    parser.add_argument("--resolve-only", action="store_true", help="Resolve claims into registry only.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of inbox items processed during extraction.")
    parser.add_argument("--teams", type=str, default="", help="Comma-separated team codes to scope ingestion/extraction, for example RR,CSK.")
    parser.add_argument("--verbose", action="store_true", help="Print source discovery and extraction debug logs.")
    args = parser.parse_args()
    global VERBOSE
    VERBOSE = args.verbose
    team_filter = parse_team_filter(args.teams)
    if team_filter:
        log_debug(f"team filter active: {sorted(team_filter)}")

    new_items: list[dict[str, Any]] = []
    extracted: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []

    if args.extract_only:
        extracted = extract_claims(limit=args.limit, team_filter=team_filter)
        print_summary(new_items, extracted, resolved)
        return
    if args.resolve_only:
        resolved = resolve_registry()
        print_summary(new_items, extracted, resolved)
        return

    if not args.extract_only and not args.resolve_only:
        new_items = ingest_sources(team_filter=team_filter)
        if args.ingest_only:
            print_summary(new_items, extracted, resolved)
            return
        extracted = extract_claims(limit=args.limit, team_filter=team_filter)
        resolved = resolve_registry()
        print_summary(new_items, extracted, resolved)


if __name__ == "__main__":
    main()
