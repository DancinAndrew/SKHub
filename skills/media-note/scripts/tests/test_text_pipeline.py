import json

import pytest

from medianote_lib import asr, subs, textclean, transcript
from medianote_lib.common import MediaNoteError, Segment, fmt_ts, parse_ts, safe_filename, ts_slug


def test_timestamp_helpers_round_trip():
    assert fmt_ts(754.9) == "12:34"
    assert fmt_ts(3723) == "01:02:03"
    assert fmt_ts(59, with_hours=True) == "00:00:59"
    assert parse_ts("1:02:03") == 3723
    assert parse_ts("12:34") == 754
    assert ts_slug(130) == "02m10s"
    assert ts_slug(3730) == "1h02m10s"


def test_parse_ts_rejects_garbage():
    with pytest.raises(MediaNoteError):
        parse_ts("12:ab")


def test_safe_filename_strips_wikilink_breakers():
    assert safe_filename('EP1 | AI#2 [draft]: "why?"') == "EP1 AI 2 draft why"
    assert safe_filename("   ") == "untitled"


def test_collapse_repeats_and_hallucination_detection():
    text, changed = textclean.collapse_repeats("一種形狀,一種形狀,一種形狀")
    assert (text, changed) == ("一種形狀", True)
    assert textclean.collapse_repeats("對，就是這樣")[1] is False
    assert textclean.is_known_hallucination("请不吝点赞 订阅 转发 打赏支持明镜与点点栏目")


def test_clean_asr_segments_flags_and_drops():
    raw = [
        {"start": 0, "end": 2, "text": "字幕由Amara.org社区提供", "language": "zh"},
        {"start": 2, "end": 4, "text": "今天講機器學習", "avg_logprob": -0.2, "language": "zh"},
        {"start": 4, "end": 6, "text": "Üxy 是不要做اء", "language": "zh"},
        {"start": 6, "end": 8, "text": "to", "language": "en"},
        {"start": 8, "end": 9, "text": "to", "language": "en"},
        {"start": 9, "end": 10, "text": "to", "language": "en"},
        {"start": 10, "end": 12, "text": "low", "avg_logprob": -1.5, "language": "en"},
    ]
    cleaned, stats = textclean.clean_asr_segments(raw)
    assert [s.text for s in cleaned] == ["今天講機器學習", "Üxy 是不要做اء", "to", "to", "low"]
    assert stats["dropped_hallucination"] == 1 and stats["dropped_duplicate"] == 1
    assert "garbled" in cleaned[1].flags
    assert "repeat" in cleaned[3].flags
    assert cleaned[4].flags == ("low-confidence",)


def test_convert_segments_only_when_simplified_detected():
    traditional = [Segment(0, 1, "這是繁體中文的句子，沒有簡體字")]
    assert textclean.convert_segments(traditional)[1] == "none"
    simplified = [Segment(0, 1, "这个视频讲的是软件和信息")]
    converted, mode = textclean.convert_segments(simplified)
    assert mode == "opencc:s2twp"
    assert "這個" in converted[0].text and "軟體" in converted[0].text
    assert textclean.convert_segments(simplified, "never")[1] == "none"


def test_parse_json3_and_vtt():
    data = {"events": [{"tStartMs": 1000, "dDurationMs": 1500, "segs": [{"utf8": "哈囉"}, {"utf8": "\n大家好"}]},
                       {"tStartMs": 3000, "dDurationMs": 500, "segs": [{"utf8": "\n"}]}]}
    assert subs.parse_json3(data) == [Segment(1.0, 2.5, "哈囉 大家好")]
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\n<c>Hello</c> world\n\n1:02:03.000 --> 1:02:04.000\nLater\n"
    assert subs.parse_vtt(vtt) == [Segment(1.0, 2.5, "Hello world"), Segment(3723.0, 3724.0, "Later")]


def test_parse_subtitle_file_dispatch(tmp_path):
    path = tmp_path / "x.zh.json3"
    path.write_text(json.dumps({"events": []}), encoding="utf-8")
    assert subs.parse_subtitle_file(path) == []
    with pytest.raises(MediaNoteError):
        subs.parse_subtitle_file(tmp_path / "x.srt")


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (["en"] * 20, [("en", 0, 20)]),
        (["en"] * 19 + ["ja"], [("en", 0, 20)]),
        (["zh"] * 8 + ["en"] * 8, [("zh", 0, 8), ("en", 8, 16)]),
        (["zh"] * 8 + ["en"] + ["zh"] * 8, [("zh", 0, 17)]),
        (["en", "zh", "zh", "zh", "zh", "zh", "en", "en", "en", "en"], [("zh", 0, 6), ("en", 6, 10)]),
    ],
)
def test_language_runs_smoothing(labels, expected):
    assert asr.language_runs(labels) == expected


def test_build_prompt_is_bounded():
    prompt = asr.build_prompt("zh", "很長的標題" * 30, ["術語"] * 50)
    assert prompt.startswith("以下是「") and len(prompt) <= asr.PROMPT_MAX_CHARS
    assert asr.build_prompt("en", "Intro", []) == 'Transcript of "Intro".'


def test_group_paragraphs_breaks_on_chapters_and_gaps():
    segs = [Segment(t, t + 1, f"s{t}") for t in (0, 5, 10, 40, 41, 100)]
    paragraphs = transcript.group_paragraphs(segs, breaks=[41])
    assert [[s.text for s in p] for p in paragraphs] == [["s0"], ["s5"], ["s10"], ["s40"], ["s41"], ["s100"]]
    dense = [Segment(t, t + 2.4, "x") for t in range(0, 70, 2)]
    assert [len(p) for p in transcript.group_paragraphs(dense, [])] == [16, 16, 3]


def test_render_markdown_marks_asr_and_flags():
    meta = {"title": "T", "source": "s", "method": "asr:m", "duration": 90,
            "chapters": [{"start": 0, "title": "開場"}], "parts": [{"file": "/a/1.m4a", "offset": 0}, {"file": "/a/2.m4a", "offset": 60}]}
    segs = [Segment(0, 3, "你好"), Segment(61, 63, "第二段", ("repeat",))]
    md = transcript.render_markdown(meta, segs)
    assert "> [!warning] 自動轉錄稿" in md
    assert "## [00:00] 章節：開場" in md and "## [01:00] 第 2 段錄音：2.m4a" in md
    assert "**[01:01]** ⚠ 第二段" in md


def test_quality_report_finds_quiet_windows():
    segs = [Segment(0, 10, "字" * 400), Segment(600, 610, "字" * 400)]
    report = transcript.quality_report(segs, duration=900)
    assert report["low_text_windows"] == ["05:00–10:00"]
    assert report["flagged_ratio"] == 0.0
