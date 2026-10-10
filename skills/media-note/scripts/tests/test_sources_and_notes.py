import json
from pathlib import Path

import pytest

from medianote_lib import checknote, podcast, vaults, youtube
from medianote_lib.common import MediaNoteError

RSS = b"""<?xml version="1.0"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<title>Gooaye</title><itunes:author>Host Name</itunes:author>
<item><title>EP2 | new</title><guid>id-2</guid><enclosure url="https://a/2.mp3"/></item>
<item><title>EP1 | old</title><guid>id-1</guid><enclosure url="https://a/1.mp3"/></item>
<item><title>no audio</title></item>
</channel></rss>"""


def test_parse_rss_and_select_episode():
    show, episodes = podcast.parse_rss(RSS)
    assert show == "Gooaye" and len(episodes) == 2 and episodes[0].author == "Host Name"
    assert podcast.select_episode(episodes, title="EP1 | old").audio_url == "https://a/1.mp3"
    assert podcast.select_episode(episodes, guid="id-2").title == "EP2 | new"
    assert podcast.select_episode(episodes, index=2).guid == "id-1"
    with pytest.raises(MediaNoteError):
        podcast.select_episode(episodes, index=5)
    with pytest.raises(MediaNoteError):
        podcast.select_episode(episodes)


def test_meta_tag_and_url_detection():
    html = '<meta property="og:title" content="EP641 | x"/><meta property="og:description" content="Gooaye 股癌 · Episode"/>'
    assert podcast._meta(html, "og:title") == "EP641 | x"
    assert podcast._meta(html, "og:description").split(" · ")[0] == "Gooaye 股癌"
    assert podcast.is_podcast_url("https://open.spotify.com/episode/abc")
    assert not podcast.is_podcast_url("https://example.com/page")


def test_youtube_helpers():
    assert youtube.is_youtube("https://www.youtube.com/watch?v=8BN8p5xDkzw&t=10s")
    assert youtube.video_id("https://youtu.be/GkUnfbPyXVA") == "GkUnfbPyXVA"
    assert not youtube.is_youtube("https://vimeo.com/123")
    assert youtube.choose_subtitle_lang(["en", "zh-TW"], "科技浪 EP154") == "zh-TW"
    assert youtube.choose_subtitle_lang(["en"], "科技浪 EP154") is None
    assert youtube.choose_subtitle_lang(["zh", "en-US"], "Stanford CS230") == "en-US"
    info = {"id": "x", "title": "t", "upload_date": "20260914", "subtitles": {"live_chat": [], "zh-TW": []},
            "automatic_captions": {"zh-TW": [], "fr": []}, "chapters": [{"start_time": 0, "end_time": 5, "title": "a"}]}
    summary = youtube.summarize_info(info)
    assert summary["upload_date"] == "2026-09-14" and summary["subtitles"] == ["zh-TW"]
    assert summary["auto_captions"] == ["zh-TW"] and summary["chapters"][0]["title"] == "a"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "Vault"
    (root / ".obsidian").mkdir(parents=True)
    (root / "未讀").mkdir()
    (root / "wiki-page.md").write_text("# page", encoding="utf-8")
    config = tmp_path / "vaults.json"
    config.write_text(json.dumps({"vaults": [{"name": "Eng", "root": str(root), "notes_dir": "未讀",
                                              "attachments_dir": "99_Attachments"}]}), encoding="utf-8")
    monkeypatch.setattr(vaults, "CONFIG", config)
    return root


def test_note_paths_and_collisions(vault):
    paths = vaults.note_paths("eng", "ML | Week 2")
    assert paths["note"].endswith("未讀/ML Week 2.md")
    assert paths["attachments_rel"] == "99_Attachments/ML Week 2"
    Path(paths["note"]).write_text("x", encoding="utf-8")
    with pytest.raises(MediaNoteError):
        vaults.note_paths("Eng", "ML | Week 2")
    with pytest.raises(MediaNoteError):
        vaults.note_paths("Nope", "x")


GOOD_NOTE = """---
title: "T"
date: 2026-09-15
source_type: youtube
source: "https://youtu.be/x"
transcript_method: "youtube-subs:zh"
duration_seconds: 300
tags:
  - type/video-note
---

# T

## 一分鐘摘要
- 重點

## 核心心智模型
- 模型

## 容易混淆的概念
- A vs B：差別

## 與既有筆記的連結
- [[wiki-page]]：補充背景

## 完整時間軸筆記

### [00:00–02:30] 開場
![[99_Attachments/T/frame-01_00m10s.jpg]]

> [!research]- 外部查證
> 已確認。
> [A](https://a.example) · [B](https://b.example)

### [02:30–05:00] 結論
- 大型語言模型（LLM）—— 會預測下一個字的模型。

## 主動回憶問題
1. 問題？
"""


def test_check_accepts_valid_note(vault):
    (vault / "99_Attachments" / "T").mkdir(parents=True)
    (vault / "99_Attachments" / "T" / "frame-01_00m10s.jpg").write_bytes(b"jpg")
    note = vault / "未讀" / "T.md"
    note.write_text(GOOD_NOTE, encoding="utf-8")
    result = checknote.check(note)
    assert result["ok"], result["errors"]
    assert result["timeline_sections"] == 2 and result["embeds"] == 1


def test_check_reports_structural_problems(vault):
    bad = (GOOD_NOTE.replace("## 容易混淆的概念\n", "")
           .replace("[02:30–05:00]", "[03:00–05:00]")
           .replace("· [B](https://b.example)", "")
           .replace("[[wiki-page]]", "[[missing-page]] TODO")
           .replace("大型語言模型（LLM）—— 會預測下一個字的模型。", "RAG 很重要"))
    note = vault / "未讀" / "Bad.md"
    note.write_text(bad, encoding="utf-8")
    result = checknote.check(note)
    joined = "\n".join(result["errors"])
    assert not result["ok"]
    for expected in ("missing heading `## 容易混淆的概念`", "30s gap", "research callout has 1", "embed not found",
                     "wikilink target not found in vault: missing-page", "placeholder text"):
        assert expected in joined
    assert any("RAG" in w for w in result["warnings"])


def test_check_rejects_type_tag_that_does_not_match_source_type(vault):
    (vault / "99_Attachments" / "T").mkdir(parents=True)
    (vault / "99_Attachments" / "T" / "frame-01_00m10s.jpg").write_bytes(b"jpg")
    note = vault / "未讀" / "WrongTag.md"
    note.write_text(GOOD_NOTE.replace("type/video-note", "type/course-note"), encoding="utf-8")
    result = checknote.check(note)
    assert not result["ok"]
    assert any("type/video-note" in e for e in result["errors"])


def test_check_skips_time_ranges_for_degraded_timeline(vault):
    (vault / "99_Attachments" / "T").mkdir(parents=True)
    (vault / "99_Attachments" / "T" / "frame-01_00m10s.jpg").write_bytes(b"jpg")
    degraded = (GOOD_NOTE.replace("source_type: youtube", "source_type: course\ntimeline_mode: degraded")
                .replace("type/video-note", "type/course-note")
                .replace("### [00:00–02:30]", "### 講述順序 1：").replace("### [02:30–05:00]", "### 講述順序 2："))
    note = vault / "未讀" / "Degraded.md"
    note.write_text(degraded, encoding="utf-8")
    result = checknote.check(note)
    assert result["ok"], result["errors"]
    assert result["timeline_sections"] == 2 and result["warnings"] == []


def test_check_accepts_grouped_four_level_timeline(vault):
    (vault / "99_Attachments" / "T").mkdir(parents=True)
    (vault / "99_Attachments" / "T" / "frame-01_00m10s.jpg").write_bytes(b"jpg")
    grouped = GOOD_NOTE.replace("### [", "#### [").replace("## 完整時間軸筆記\n", "## 完整時間軸筆記\n\n### 第一組\n")
    note = vault / "未讀" / "Grouped.md"
    note.write_text(grouped, encoding="utf-8")
    result = checknote.check(note)
    assert result["ok"], result["errors"]
    assert result["timeline_sections"] == 2


def test_acronym_scan_looks_inside_callouts_but_skips_their_tables():
    body = "> [!warning]- 校正\n> | 聽成 | 實際 |\n> | --- | --- |\n> | CBCL | SimCLR |\n> 這段提到 RAG 沒有解釋\n"
    assert checknote._unexplained_acronyms(body) == ["RAG"]


def test_acronym_scan_ignores_code_links_and_urls():
    body = "```mermaid\nflowchart LR\n```\n[[KP FOMO研究院/x|別名]] 與 [來源](https://x.com/ABC) 以及 RAG 很重要\n另外 LLMs 也是\n"
    assert checknote._unexplained_acronyms(body) == ["RAG", "LLM"]


def test_check_rejects_space_indented_list_items(vault):
    note = vault / "未讀" / "Spaced.md"
    note.write_text(GOOD_NOTE.replace("- 大型語言模型", "  - 大型語言模型"), encoding="utf-8")
    result = checknote.check(note)
    assert not result["ok"]
    assert any("indented with spaces" in e for e in result["errors"])


def test_list_indentation_accepts_tabs_and_skips_frontmatter_and_code():
    lines = ["---", "tags:", "  - type/course-note", "---", "- 父項", "\t- 子項", "\t\t- 孫項",
             "```", "  - 這是程式碼", "```", "  1. 空格編號子項"]
    assert checknote._list_indentation(lines) == ["line 11: list item indented with spaces; use one tab per level"]
