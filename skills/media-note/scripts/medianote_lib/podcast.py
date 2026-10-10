"""Resolve public podcast episodes (RSS, Apple Podcasts, SoundOn, Spotify) to downloadable audio."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .common import MediaNoteError, log, read_json, short_hash, work_dir, write_json

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) media-note/1.0"
HTTP_TIMEOUT_S = 60
DOWNLOAD_TIMEOUT_S = 600
MAX_PAGE_BYTES = 20 * 1024 * 1024          # RSS feeds, HTML pages, JSON lookups
MAX_AUDIO_BYTES = 2 * 1024 * 1024 * 1024   # one episode; anything larger is not a podcast
COPY_CHUNK_BYTES = 1024 * 1024
ITUNES_COUNTRY = "tw"
AUDIO_EXTENSIONS = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac")


@dataclass(frozen=True)
class Episode:
    title: str
    audio_url: str
    show: str | None = None
    published: str | None = None
    page_url: str | None = None
    guid: str | None = None
    author: str | None = None


def _get(url: str, timeout: float = HTTP_TIMEOUT_S) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_PAGE_BYTES + 1)
    except Exception as exc:  # urllib raises several unrelated types
        raise MediaNoteError(f"HTTP request failed for {url}: {exc}") from exc
    if len(body) > MAX_PAGE_BYTES:
        raise MediaNoteError(f"Response from {url} exceeds {MAX_PAGE_BYTES // 1024 // 1024} MiB; refusing to parse it.")
    return body


def _get_json(url: str) -> Any:
    return json.loads(_get(url).decode("utf-8", errors="replace"))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child(item: ET.Element, name: str) -> str:
    for child in item:
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _enclosure(item: ET.Element) -> str:
    return next((c.attrib.get("url", "") for c in item if _local(c.tag) == "enclosure"), "")


def parse_rss(xml_bytes: bytes) -> tuple[str, list[Episode]]:
    if b"<!ENTITY" in xml_bytes:
        raise MediaNoteError("Feed declares XML entities; refusing to parse it (possible entity-expansion attack).")
    root = ET.fromstring(xml_bytes)
    channel = next((el for el in root.iter() if _local(el.tag) == "channel"), root)
    show = _child(channel, "title")
    author = _child(channel, "author") or None
    episodes = [
        Episode(title=_child(item, "title"), audio_url=_enclosure(item), show=show, published=_child(item, "pubdate") or None,
                page_url=_child(item, "link") or None, guid=_child(item, "guid") or None, author=author)
        for item in root.iter() if _local(item.tag) == "item"
    ]
    return show, [ep for ep in episodes if ep.audio_url]


def _norm(text: str) -> str:
    return re.sub(r"[\W_]+", "", text).lower()


def select_episode(episodes: list[Episode], *, title: str | None = None, guid: str | None = None,
                   index: int | None = None) -> Episode:
    if guid:
        matches = [ep for ep in episodes if guid in " ".join(filter(None, [ep.guid, ep.page_url, ep.audio_url]))]
    elif title:
        needle = _norm(title)
        exact = [ep for ep in episodes if _norm(ep.title) == needle]
        matches = exact or [ep for ep in episodes if needle in _norm(ep.title)]
    elif index:
        if not 1 <= index <= len(episodes):
            raise MediaNoteError(f"--episode-index must be between 1 and {len(episodes)}")
        return episodes[index - 1]
    else:
        raise MediaNoteError("For an RSS feed pass --episode-title, --episode-guid or --episode-index.")
    if not matches:
        raise MediaNoteError("No RSS item matched the requested episode.")
    if len(matches) > 1:
        log(f"{len(matches)} episodes matched; using the first: {matches[0].title}")
    return matches[0]


def _itunes_search(term: str, entity: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"term": term, "media": "podcast", "entity": entity, "country": ITUNES_COUNTRY, "limit": 25})
    return _get_json(f"https://itunes.apple.com/search?{query}").get("results", [])


def _meta(html: str, prop: str) -> str:
    match = re.search(r'<meta[^>]+(?:property|name)="' + re.escape(prop) + r'"[^>]+content="([^"]*)"', html)
    return match.group(1).strip() if match else ""


def find_public_episode(show: str, title: str) -> Episode:
    """Locate an episode in the show's public feed (exact title), falling back to Apple's episode search."""
    shows = [r for r in _itunes_search(show, "podcast") if _norm(r.get("collectionName", "")) == _norm(show)]
    feed = next((r["feedUrl"] for r in shows if r.get("feedUrl")), None)
    if feed:
        _, episodes = parse_rss(_get(feed))
        exact = [ep for ep in episodes if _norm(ep.title) == _norm(title)]
        if exact:
            return exact[0]
    hits = [r for r in _itunes_search(f"{show} {title}", "podcastEpisode")
            if _norm(r.get("trackName", "")) == _norm(title) and _norm(r.get("collectionName", "")) == _norm(show)]
    if not hits or not hits[0].get("episodeUrl"):
        raise MediaNoteError(f"No public audio found for {show!r} / {title!r}; ask the user for the RSS or Apple Podcasts link.")
    hit = hits[0]
    return Episode(title=hit["trackName"], audio_url=hit["episodeUrl"], show=hit.get("collectionName"),
                   published=hit.get("releaseDate"), page_url=hit.get("trackViewUrl"), guid=str(hit.get("trackId")),
                   author=hit.get("artistName"))


def _from_apple(url: str) -> Episode:
    show_id = re.search(r"/id(\d+)", url)
    episode_id = re.search(r"[?&]i=(\d+)", url)
    if not show_id or not episode_id:
        raise MediaNoteError("Apple Podcasts links must point to one episode (…/id<show>?i=<episode>).")
    query = urllib.parse.urlencode({"id": show_id.group(1), "entity": "podcastEpisode", "limit": 200, "country": ITUNES_COUNTRY})
    results = _get_json(f"https://itunes.apple.com/lookup?{query}").get("results", [])
    hit = next((r for r in results if str(r.get("trackId")) == episode_id.group(1)), None)
    if hit and hit.get("episodeUrl"):
        return Episode(title=hit["trackName"], audio_url=hit["episodeUrl"], show=hit.get("collectionName"),
                       published=hit.get("releaseDate"), page_url=url, guid=episode_id.group(1),
                       author=hit.get("artistName"))
    feed = next((r.get("feedUrl") for r in results if r.get("feedUrl")), None)
    if not feed:
        raise MediaNoteError("Episode not in the Apple lookup window and the show has no public feed.")
    raise MediaNoteError(f"Episode is older than Apple's lookup window; rerun with the RSS feed {feed} and --episode-title.")


def _from_spotify(url: str) -> Episode:
    if "/episode/" not in url:
        raise MediaNoteError("Spotify links must point to a single episode (open.spotify.com/episode/…).")
    html = _get(url.split("?")[0]).decode("utf-8", errors="replace")
    title = _meta(html, "og:title")
    show = _meta(html, "og:description").split(" · ")[0].strip()
    if not title or not show:
        raise MediaNoteError("Could not read episode title/show from the Spotify page; ask the user for another link.")
    episode = find_public_episode(show, title)
    return Episode(**{**asdict(episode), "page_url": url})


def _from_soundon(url: str) -> Episode:
    ids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", url)
    if len(ids) < 2:
        raise MediaNoteError("SoundOn links must include both podcast and episode ids.")
    _, episodes = parse_rss(_get(f"https://feeds.soundon.fm/podcasts/{ids[0]}.xml"))
    return select_episode(episodes, guid=ids[1])


def resolve(url: str, *, title: str | None = None, guid: str | None = None, index: int | None = None) -> Episode:
    host = urllib.parse.urlparse(url).netloc.lower()
    path = urllib.parse.urlparse(url).path.lower()
    if "spotify.com" in host:
        return _from_spotify(url)
    if "podcasts.apple.com" in host:
        return _from_apple(url)
    if "soundon.fm" in host and "feeds." not in host:
        return _from_soundon(url)
    if path.endswith(AUDIO_EXTENSIONS):
        return Episode(title=title or Path(path).stem, audio_url=url)
    _, episodes = parse_rss(_get(url))
    return select_episode(episodes, title=title, guid=guid, index=index)


def is_podcast_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(h in host for h in ("spotify.com", "podcasts.apple.com", "soundon.fm")) or bool(
        re.search(r"(rss|feed|\.xml)", url.lower())) or urllib.parse.urlparse(url).path.lower().endswith(AUDIO_EXTENSIONS)


def download(episode: Episode) -> tuple[Path, Path]:
    work = work_dir("pod-" + short_hash(episode.audio_url))
    write_json(work / "episode.json", asdict(episode))
    suffix = Path(urllib.parse.urlparse(episode.audio_url).path).suffix or ".mp3"
    target = work / "audio" / f"episode{suffix if suffix in AUDIO_EXTENSIONS else '.mp3'}"
    if target.exists():
        return work, target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    log(f"downloading {episode.audio_url}")
    request = urllib.request.Request(episode.audio_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_S) as response, partial.open("wb") as handle:
            copied = 0
            while chunk := response.read(COPY_CHUNK_BYTES):
                copied += len(chunk)
                if copied > MAX_AUDIO_BYTES:
                    raise MediaNoteError(f"Audio exceeds {MAX_AUDIO_BYTES // 1024 ** 3} GiB; aborting download.")
                handle.write(chunk)
    except Exception as exc:
        partial.unlink(missing_ok=True)
        if isinstance(exc, MediaNoteError):
            raise
        raise MediaNoteError(f"Audio download failed: {exc}") from exc
    partial.replace(target)
    return work, target


def load_episode(work: Path) -> Episode:
    return Episode(**read_json(work / "episode.json"))
