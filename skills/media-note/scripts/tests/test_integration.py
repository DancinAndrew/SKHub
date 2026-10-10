"""Integration tests with synthetic media (ffmpeg/poppler required) and faked network/ASR calls."""

import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import medianote
from medianote_lib import asr, common, frames, pdfpages, podcast, vaults, youtube
from medianote_lib.common import MediaNoteError


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "CACHE_ROOT", tmp_path / "cache")


def _pattern(seed: int) -> Image.Image:
    blocks = np.random.default_rng(seed).integers(0, 256, size=(9, 16), dtype=np.uint8)
    return Image.fromarray(blocks, mode="L").resize((320, 180), Image.NEAREST).convert("RGB")


@pytest.fixture
def video(tmp_path) -> Path:
    """24 s: a recurring 'host' card (seed 0) between four different 'charts', each held 3 s."""
    order = [0, 1, 0, 2, 0, 3, 0, 4]
    frames_dir = tmp_path / "src"
    frames_dir.mkdir()
    index = 0
    for seed in order:
        for _ in range(3):
            _pattern(seed).save(frames_dir / f"f{index:03d}.png")
            index += 1
    out = tmp_path / "talk.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(frames_dir / "f%03d.png"),
                    "-r", "5", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


@pytest.fixture
def pdf(tmp_path) -> Path:
    pages = [_pattern(seed) for seed in (7, 8, 9)]
    out = tmp_path / "Deck One.pdf"
    pages[0].save(out, save_all=True, append_images=pages[1:])
    return out


@pytest.fixture
def audio(tmp_path) -> Path:
    out = tmp_path / "lecture 1.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                    "-c:a", "aac", str(out)], check=True)
    return out


@pytest.fixture
def vault(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "Vault"
    (root / ".obsidian").mkdir(parents=True)
    (root / "未讀").mkdir()
    config = tmp_path / "vaults.json"
    config.write_text(json.dumps({"vaults": [{"name": "Eng", "root": str(root), "notes_dir": "未讀",
                                              "attachments_dir": "99_Attachments"}]}), encoding="utf-8")
    monkeypatch.setattr(vaults, "CONFIG", config)
    return root


def run_cli(capsys, *argv: str) -> tuple[int, dict]:
    code = medianote.main(list(argv))
    return code, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_frames_pipeline_skips_recurring_host_and_exports(video, vault, capsys):
    code, result = run_cli(capsys, "frames", str(video))
    assert code == 0 and result["candidates"] == 4 and result["recurring_count"] == 4
    assert all(Path(p).is_file() for p in result["sheets"] + result["recurring_sheets"])
    dest = vault / "99_Attachments" / "Talk"
    code, exported = run_cli(capsys, "export-frames", "--work", result["work_dir"], "--pick", "2,4", "--dest", str(dest))
    assert code == 0
    assert [e["embed"] for e in exported["exported"]] == ["![[99_Attachments/Talk/frame-01_00m11s.jpg]]",
                                                         "![[99_Attachments/Talk/frame-02_00m23s.jpg]]"]
    code, again = run_cli(capsys, "export-frames", "--work", result["work_dir"], "--pick", "2", "--dest", str(dest))
    assert code == 1 and "Refusing to overwrite" in again["error"]
    with pytest.raises(MediaNoteError):
        frames.export_frames(Path(result["work_dir"]), [99], dest)


def test_pdf_extract_export_and_align(pdf, tmp_path, vault, capsys):
    code, result = run_cli(capsys, "pdf", str(pdf))
    deck = result["decks"][0]
    assert code == 0 and deck["page_count"] == 3 and deck["low_text_pages"] == [1, 2, 3]
    dest = vault / "99_Attachments" / "Deck"
    code, exported = run_cli(capsys, "export-pages", "--pdf", str(pdf), "--pages", "2,3", "--dest", str(dest))
    assert code == 0 and exported["exported"][0]["embed"] == "![[99_Attachments/Deck/Deck_One-p02.jpg]]"
    assert run_cli(capsys, "export-pages", "--pdf", str(pdf), "--pages", "2", "--dest", str(dest))[1]["exported"][0]["reused"]
    assert run_cli(capsys, "export-pages", "--pdf", str(pdf), "--pages", "9", "--dest", str(dest))[0] == 1
    png = pdfpages.export_pages(pdf, [1], tmp_path / "png", fmt="png")
    assert png[0]["file"].endswith(".png") and Path(png[0]["file"]).is_file()
    work = tmp_path / "work"
    work.mkdir()
    (work / "transcript.json").write_text(json.dumps({"segments": [{"start": 0, "end": 5, "text": "hello"}]}), encoding="utf-8")
    code, aligned = run_cli(capsys, "align", "--work", str(work), "--pdf", str(pdf))
    assert code == 0 and aligned["spans"] == 1 and Path(aligned["alignment_md"]).is_file()


def test_asr_language_runs_drive_clipped_transcription(audio, tmp_path, monkeypatch):
    monkeypatch.setattr(asr, "require_mlx", lambda: None)
    monkeypatch.setattr(asr, "detect_window_languages", lambda wav, model: ["zh"] * 4 + ["en"] * 4)
    calls = []

    def fake_run(wav, work, language, start_s, end_s, model_name, prompt):
        calls.append((language, start_s, end_s, prompt[:4]))
        return [{"start": start_s, "end": start_s + 1, "text": language, "language": language}]

    monkeypatch.setattr(asr, "_transcribe_run", fake_run)
    kwargs = dict(model_name="m", language=None, title="課", terms=["GAN"], max_seconds=None)
    result = asr.transcribe_file(audio, tmp_path, **kwargs)
    assert calls == [("zh", 0.0, 120, "以下是「"), ("en", 120.0, None, "Tran")]
    assert [r["language"] for r in result["language_runs"]] == ["zh", "en"]
    assert asr.transcribe_file(audio, tmp_path, **kwargs) == result and len(calls) == 2  # cache hit
    assert not list((tmp_path / "asr").glob("*.wav"))


def test_asr_explains_missing_metal_gpu(audio, tmp_path, monkeypatch):
    def no_gpu(name):
        raise ImportError("[metal::load_device] No Metal device available.")

    monkeypatch.setattr(asr.importlib, "import_module", no_gpu)
    with pytest.raises(MediaNoteError, match="outside the sandbox"):
        asr.transcribe_file(audio, tmp_path, model_name="m", language="en", title="t", terms=[], max_seconds=2)
    monkeypatch.setattr(asr.importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError("no module")))
    with pytest.raises(MediaNoteError, match="not usable"):
        asr.require_mlx()


def test_asr_rejects_empty_output(audio, tmp_path, monkeypatch):
    monkeypatch.setattr(asr, "require_mlx", lambda: None)
    monkeypatch.setattr(asr, "_transcribe_run", lambda *a, **k: [])
    with pytest.raises(MediaNoteError, match="no text"):
        asr.transcribe_file(audio, tmp_path, model_name="m", language="en", title="t", terms=[], max_seconds=2)


def test_transcript_command_local_route(audio, pdf, capsys, monkeypatch):
    seen = {}

    def fake_transcribe(path, work, **kwargs):
        seen.update(kwargs)
        return {"duration": 5.0, "elapsed_s": 0.1, "language_runs": [{"language": "zh", "start": 0, "end": None}],
                "segments": [{"start": 0.5, "end": 2, "text": "这是简体的课程", "language": "zh"},
                             {"start": 2, "end": 3, "text": "谢谢 谢谢 谢谢 谢谢", "language": "zh"}]}

    monkeypatch.setattr(asr, "transcribe_file", fake_transcribe)
    code, result = run_cli(capsys, "probe", str(audio))
    assert code == 0 and result["total_duration"] == "00:00:05"
    code, result = run_cli(capsys, "transcript", str(audio), str(audio), "--title", "課程", "--terms", "GAN, CNN")
    assert code == 0 and result["conversion"] == "opencc:s2twp" and len(result["parts"]) == 2
    assert result["parts"][1]["offset"] == 5.0 and seen["terms"] == ["GAN", "CNN"]
    text = Path(result["transcript_md"]).read_text(encoding="utf-8")
    assert "這是簡體的課程" in text and "## [00:05] 第 2 段錄音" in text and "⚠ 謝謝" in text
    assert run_cli(capsys, "transcript", "/nope/missing.m4a")[0] == 1


def test_transcript_command_youtube_subtitle_route(tmp_path, capsys, monkeypatch):
    info = {"id": "abcdefghijk", "title": "科技浪 EP1", "channel": "科技浪", "upload_date": "2026-09-14", "duration": 120,
            "webpage_url": "https://www.youtube.com/watch?v=abcdefghijk", "description": "d", "live_status": None,
            "chapters": [{"start": 0, "end": 60, "title": "開場"}], "subtitles": ["zh-TW"], "auto_captions": []}
    sub_file = tmp_path / "abcdefghijk.zh-TW.vtt"
    sub_file.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n哈囉\n\n00:01:30.000 --> 00:01:31.000\n後面\n", encoding="utf-8")
    monkeypatch.setattr(youtube, "fetch_info", lambda url, work: info)
    monkeypatch.setattr(youtube, "fetch_subtitles", lambda url, lang, work: sub_file)
    url = "https://www.youtube.com/watch?v=abcdefghijk"
    code, probe = run_cli(capsys, "probe", url)
    assert code == 0 and probe["transcript_plan"] == "youtube-subs:zh-TW" and probe["asr_estimate"] is None
    code, result = run_cli(capsys, "transcript", url, "--max-seconds", "60")
    assert code == 0 and result["method"] == "youtube-subs:zh-TW" and result["chapters"] == 1
    assert "後面" not in Path(result["transcript_md"]).read_text(encoding="utf-8")


def test_youtube_wrappers_with_fake_ytdlp(tmp_path, monkeypatch):
    calls = []

    def fake(args, timeout):
        calls.append(args)
        if "--dump-single-json" in args:
            return json.dumps({"id": "abcdefghijk", "title": "T", "subtitles": {"en": []}, "duration": 3})
        target = Path(args[args.index("-o") + 1])
        if "--write-subs" in args:
            (target.parent / "abcdefghijk.en.json3").parent.mkdir(parents=True, exist_ok=True)
            (target.parent / "abcdefghijk.en.json3").write_text("{}", encoding="utf-8")
        elif "--impersonate" in args:
            raise MediaNoteError("Impersonate target chrome is not available")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            (target.parent / "abcdefghijk.audio.m4a").write_bytes(b"x")
        return ""

    monkeypatch.setattr(youtube, "_ytdlp", fake)
    url = "https://youtu.be/abcdefghijk"
    assert youtube.fetch_info(url, tmp_path)["title"] == "T"
    assert youtube.fetch_info(url, tmp_path)["title"] == "T" and len(calls) == 1
    assert youtube.fetch_subtitles(url, "en", tmp_path).name == "abcdefghijk.en.json3"
    assert youtube.download_audio(url, tmp_path).name == "abcdefghijk.audio.m4a"
    assert sum("--impersonate" in c for c in calls) == 1
    assert youtube.download_audio(url, tmp_path).name == "abcdefghijk.audio.m4a"  # already downloaded
    with pytest.raises(MediaNoteError):
        youtube.fetch_subtitles(url, "fr", tmp_path)


def test_ytdlp_bot_check_is_explained(monkeypatch):
    def refuse(cmd, timeout=None):
        raise MediaNoteError("ERROR: [youtube] x: Sign in to confirm you’re not a bot")

    monkeypatch.setattr(youtube, "run", refuse)
    with pytest.raises(MediaNoteError, match="cookies-from-browser"):
        youtube.fetch_info("https://youtu.be/abcdefghijk", Path("/nonexistent-cache"))


RSS = b"""<rss><channel><title>Gooaye</title><author>Host</author>
<item><title>EP641 | x</title><guid>aaaaaaaa-1111-2222-3333-444444444444</guid><enclosure url="https://cdn/641.mp3"/></item>
</channel></rss>"""


def test_podcast_resolvers_with_fake_http(monkeypatch, capsys):
    def fake_get(url, timeout=60):
        if "spotify.com" in url:
            return b'<meta property="og:title" content="EP641 | x"><meta property="og:description" content="Gooaye \xc2\xb7 Episode">'
        if "itunes.apple.com/search" in url:
            return json.dumps({"results": [{"collectionName": "Gooaye", "feedUrl": "https://feed/x.xml"}]}).encode()
        if "itunes.apple.com/lookup" in url:
            return json.dumps({"results": [{"trackId": 99, "trackName": "EP641 | x", "episodeUrl": "https://cdn/a.mp3",
                                            "collectionName": "Gooaye", "artistName": "Host"}]}).encode()
        return RSS

    monkeypatch.setattr(podcast, "_get", fake_get)
    assert podcast.resolve("https://open.spotify.com/episode/abc").audio_url == "https://cdn/641.mp3"
    assert podcast.resolve("https://podcasts.apple.com/tw/podcast/x/id123?i=99").author == "Host"
    soundon = "https://player.soundon.fm/p/bbbbbbbb-1111-2222-3333-444444444444/episodes/aaaaaaaa-1111-2222-3333-444444444444"
    assert podcast.resolve(soundon).title == "EP641 | x"
    assert podcast.resolve("https://feed/x.xml", index=1).guid == "aaaaaaaa-1111-2222-3333-444444444444"
    assert podcast.resolve("https://cdn/file.mp3").title == "file"
    with pytest.raises(MediaNoteError):
        podcast.resolve("https://podcasts.apple.com/tw/podcast/x/id123?i=5")
    with pytest.raises(MediaNoteError):
        podcast.resolve("https://open.spotify.com/show/abc")
    code, probe = run_cli(capsys, "probe", "https://feed/x.xml", "--episode-index", "1")
    assert code == 0 and probe["show"] == "Gooaye"


def test_podcast_download_writes_once(monkeypatch):
    opened = []

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        opened.append(request.full_url)
        return FakeResponse(b"ID3audio")

    monkeypatch.setattr(podcast.urllib.request, "urlopen", fake_urlopen)
    episode = podcast.Episode(title="EP", audio_url="https://cdn/ep.mp3?x=1", show="S")
    work, path = podcast.download(episode)
    assert path.read_bytes() == b"ID3audio" and podcast.load_episode(work) == episode
    assert podcast.download(episode)[1] == path and len(opened) == 1


def test_podcast_size_limits_and_entity_feeds(monkeypatch):
    with pytest.raises(MediaNoteError, match="entities"):
        podcast.parse_rss(b'<!DOCTYPE r [<!ENTITY a "x">]><rss><channel><title>&a;</title></channel></rss>')

    class Endless(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(podcast, "MAX_PAGE_BYTES", 10)
    monkeypatch.setattr(podcast, "MAX_AUDIO_BYTES", 10)
    monkeypatch.setattr(podcast, "COPY_CHUNK_BYTES", 4)
    monkeypatch.setattr(podcast.urllib.request, "urlopen", lambda request, timeout=None: Endless(b"x" * 64))
    with pytest.raises(MediaNoteError, match="exceeds"):
        podcast._get("https://example.com/feed.xml")
    with pytest.raises(MediaNoteError, match="aborting"):
        podcast.download(podcast.Episode(title="big", audio_url="https://cdn/big.mp3"))
    assert not list(common.CACHE_ROOT.rglob("*.part"))


def test_file_fingerprint_sees_middle_edits(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    body = bytearray(b"x" * (3 << 20))
    a.write_bytes(bytes(body))
    body[len(body) // 2] = ord("y")
    b.write_bytes(bytes(body))
    assert common.file_fingerprint(a) != common.file_fingerprint(b)


def test_vault_paths_and_check_commands(vault, capsys):
    code, paths = run_cli(capsys, "paths", "--vault", "Eng", "--title", "筆記 A", "--folder", "")
    assert code == 0 and paths["note"] == str(vault / "筆記 A.md")
    assert run_cli(capsys, "vaults")[1]["vaults"][0]["name"] == "Eng"
    for escape in ("../outside", "/tmp"):
        code, refused = run_cli(capsys, "paths", "--vault", "Eng", "--title", "x", "--folder", escape)
        assert code == 1 and "inside the vault" in refused["error"]
    note = vault / "未讀" / "empty.md"
    note.write_text("no frontmatter", encoding="utf-8")
    code, result = run_cli(capsys, "check", str(note))
    assert code == 2 and "missing YAML frontmatter" in result["errors"]
    assert run_cli(capsys, "check", str(vault / "missing.md"))[0] == 1
