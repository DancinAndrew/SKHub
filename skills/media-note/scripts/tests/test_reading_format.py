import hashlib
import json
from pathlib import Path

from medianote_lib import checknote

ARTICLE = '''---
title: T
date: 2026-10-09
source_type: youtube
source: https://youtu.be/x
transcript_method: youtube-subs:zh
duration_seconds: 300
note_style: reading-v3
generator: media-note
skill_version: 3.0.0
tags:
  - type/video-note
---
# T

這一集先提出問題，再比較兩種安排。

## 取得資金為何不等於改變趨勢
先講取得現金，再講需求是否改變。

![資金順序與價格條件的對照](figure.svg)
*整理者總覽；原節目的兩個不同問題。*

> [!note]- 查證：制度適用範圍
> 官方原始文件說明工具條件，不能證明動機。
> [官方](https://official.example/rule)

*[回聽 00:00–05:00](https://youtu.be/x?t=0s)。*
'''


def make_note(tmp_path):
    root = tmp_path / 'Vault'
    (root / '.obsidian').mkdir(parents=True)
    (root / 'figure.svg').write_text('<svg/>')
    note = root / 'T.md'
    note.write_text(ARTICLE)
    return note


def test_article_structure_does_not_claim_semantic_validation(tmp_path):
    result = checknote.check(make_note(tmp_path))
    assert result['ok'], result['errors']
    assert result['format'] == 'reading-v3'
    assert result['validation_scope'] == 'structure-only'
    assert result['semantic_review'] == 'required'
    assert result['coverage_status'] == 'not-supplied'
    assert result['embeds'] == 1


def test_article_rejects_broken_image_and_wrong_return_link(tmp_path):
    note = make_note(tmp_path)
    note.write_text(ARTICLE.replace('figure.svg', 'missing.svg').replace('t=0s', 't=90s'))
    errors = checknote.check(note)['errors']
    assert any('Markdown image not found' in e for e in errors)
    assert any('link time differs' in e for e in errors)


def test_article_rejects_reversed_range_bad_clock_and_duration(tmp_path):
    note = make_note(tmp_path)
    note.write_text(ARTICLE.replace('00:00–05:00', '06:70–05:00'))
    errors = checknote.check(note)['errors']
    assert any('invalid clock' in e for e in errors)
    assert any('ends before' in e for e in errors)
    note.write_text(ARTICLE.replace('00:00–05:00', '00:00–06:00'))
    assert any('exceeds source duration' in e for e in checknote.check(note)['errors'])


def test_single_nonprimary_research_link_is_not_enough(tmp_path):
    note = make_note(tmp_path)
    note.write_text(ARTICLE.replace('官方原始文件', '媒體評論'))
    assert any('needs 2' in e for e in checknote.check(note)['errors'])


def coverage_for(note, source):
    return {'source': 'https://youtu.be/x', 'source_file': str(source),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'note_sha256': hashlib.sha256(note.read_bytes()).hexdigest(),
            'units': [{'id': 'U1', 'start': 0, 'end': 300, 'role': '推理',
                       'required': '取得資金與改變趨勢的區別', 'action': '保留',
                       'article_location': '取得資金為何不等於改變趨勢', 'rationale': '保留兩個條件'}]}


def test_coverage_checks_actual_source_and_note_identity(tmp_path):
    note = make_note(tmp_path)
    source = tmp_path / 'transcript.md'
    source.write_text('原始逐字稿')
    data = coverage_for(note, source)
    manifest = tmp_path / 'coverage.json'
    manifest.write_text(json.dumps(data))
    result = checknote.check(note, manifest)
    assert result['ok'] and result['coverage_status'] == 'metadata-verified'
    assert result['semantic_review'] == 'required'
    source.write_text('被改動的逐字稿')
    assert any('source_sha256' in e for e in checknote.check(note, manifest)['errors'])
    source.write_text('原始逐字稿')
    note.write_text(ARTICLE + '\n新內容\n')
    assert any('note_sha256' in e for e in checknote.check(note, manifest)['errors'])


def test_unknown_coverage_stays_explicit_and_duplicate_ids_fail(tmp_path):
    note = make_note(tmp_path)
    source = tmp_path / 'source.md'
    source.write_text('原始')
    data = coverage_for(note, source)
    data['units'][0]['action'] = '未知'
    manifest = tmp_path / 'coverage.json'
    manifest.write_text(json.dumps(data))
    result = checknote.check(note, manifest)
    assert result['ok'] and any('unresolved' in w for w in result['warnings'])
    data['units'].append(data['units'][0])
    manifest.write_text(json.dumps(data))
    assert not checknote.check(note, manifest)['ok']


def test_legacy_last_interval_is_checked(tmp_path):
    errors, _, _ = checknote._timeline(['### [00:00–00:10] first', '### [00:10–00:05] last'], 10)
    assert any('ends before' in e for e in errors)


def test_code_is_not_read_as_wikilinks_or_acronyms(tmp_path):
    note = make_note(tmp_path)
    code = (
        "\n```python\nX = auto[['horsepower', 'width']]  # SIMCLR ABCD\n```\n\n"
        "> [!example]- 練習\n> ```python\n> X = auto[['width', 'engine-size']]\n> ```\n\n"
        "檔案 `Paper-SIMCLR.pdf` 與 `df[['a']]`。\n"
    )
    note.write_text(ARTICLE.replace("先講取得現金，再講需求是否改變。", "先講取得現金，再講需求是否改變。" + code))
    result = checknote.check(note)
    assert result['ok'], result['errors']
    assert not any('SIMCLR' in w or 'ABCD' in w for w in result['warnings'])


def test_pdf_page_link_resolves_to_the_pdf(tmp_path):
    note = make_note(tmp_path)
    (note.parent / 'Slides.pdf').write_bytes(b'%PDF')
    linked = ARTICLE.replace("先講取得現金", "見 [[Slides.pdf#page=3|講義 p.3]]，先講取得現金")
    note.write_text(linked)
    assert checknote.check(note)['ok']
    note.write_text(linked.replace('Slides.pdf#', 'Missing.pdf#'))
    assert any('Missing.pdf' in e for e in checknote.check(note)['errors'])
