"""Candidate mapping from transcript time windows to slide pages: TF-IDF similarity plus a monotonic Viterbi path."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .common import Segment, fmt_ts

WINDOW_S = 60
START_SKIP_COST = 0.01       # per page skipped before the first matched page
SKIP_COST = 0.02             # per page jumped over when moving forward
ADVANCE_COST = 0.005
BACKWARD_COST = 0.12         # lecturers do flip back, but rarely
NULL_SCORE = 0.05            # emission of "no slide matches this window"
NULL_SWITCH_COST = 0.03
TOP_ALTERNATIVES = 3
EN_STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its itself just let like me more most my no nor not now of off on once only or other our out over
own really right same she should so some such than that the their them then there these they this those through to
too under until up very was we were what when where which while who whom why will with would you your yours okay ok
yeah um uh gonna actually kind thing things lot see know think going get got one two also us let's say
""".split())
ZH_STOP_BIGRAMS = frozenset("我們 你們 他們 這個 那個 就是 然後 所以 一個 什麼 可以 因為 如果 還是 其實 大家 今天 這樣 那麼 現在 的話 一下 有沒 沒有 是不".split())


@dataclass(frozen=True)
class Page:
    deck: str
    page: int
    title: str
    text: str

    @property
    def ref(self) -> str:
        return f"{self.deck} p.{self.page}"


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9+#'-]*", text):
        token = word.lower().strip("'-")
        if len(token) < 2 or token in EN_STOPWORDS:
            continue
        if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    tokens += re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)
    for run_ in re.findall(r"[一-鿿]+", text):
        tokens += [bigram for bigram in (run_[i:i + 2] for i in range(len(run_) - 1)) if bigram not in ZH_STOP_BIGRAMS]
    return tokens


def idf_weights(documents: list[list[str]]) -> dict[str, float]:
    df = Counter(token for doc in documents for token in set(doc))
    total = len(documents)
    return {token: math.log((total + 1) / (count + 1)) + 1.0 for token, count in df.items()}


def tfidf(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(t for t in tokens if t in idf)
    vector = {token: (1 + math.log(n)) * idf[token] for token, n in counts.items()}
    norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
    return {token: v / norm for token, v in vector.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(token, 0.0) for token, weight in a.items())


def windows(segments: list[Segment], size: float = WINDOW_S) -> list[tuple[float, float, str]]:
    buckets: dict[int, list[Segment]] = {}
    for seg in segments:
        buckets.setdefault(int(seg.start // size), []).append(seg)
    return [(index * size, (index + 1) * size, " ".join(s.text for s in buckets[index])) for index in sorted(buckets)]


def viterbi(scores: list[list[float]]) -> list[int | None]:
    """Best page per window (None = no slide), favouring forward progress through the decks."""
    if not scores:
        return []
    pages = len(scores[0])
    null = pages
    best = [scores[0][p] - START_SKIP_COST * p for p in range(pages)] + [NULL_SCORE]
    back: list[list[int]] = []
    for row in scores[1:]:
        pointers, current = [], []
        for q in range(pages + 1):
            emission = NULL_SCORE if q == null else row[q]
            candidates = []
            for p in range(pages + 1):
                if p == q:
                    cost = 0.0
                elif p == null or q == null:
                    cost = NULL_SWITCH_COST
                elif q > p:
                    cost = ADVANCE_COST + SKIP_COST * (q - p - 1)
                else:
                    cost = BACKWARD_COST
                candidates.append((best[p] - cost, p))
            value, pointer = max(candidates)
            current.append(value + emission)
            pointers.append(pointer)
        best = current
        back.append(pointers)
    state = max(range(pages + 1), key=lambda s: best[s])
    path = [state]
    for pointers in reversed(back):
        state = pointers[state]
        path.append(state)
    path.reverse()
    return [None if s == null else s for s in path]


def align(segments: list[Segment], pages: list[Page]) -> dict[str, Any]:
    page_tokens = [tokenize(f"{p.title} {p.text}") for p in pages]
    idf = idf_weights(page_tokens)
    page_vectors = [tfidf(tokens, idf) for tokens in page_tokens]
    spans_in = windows(segments)
    scores = [[cosine(tfidf(tokenize(text), idf), vec) for vec in page_vectors] for _, _, text in spans_in]
    path = viterbi(scores)
    rows = []
    for (start, end, _), row, state in zip(spans_in, scores, path):
        ranked = sorted(range(len(pages)), key=lambda i: row[i], reverse=True)[:TOP_ALTERNATIVES]
        rows.append({
            "start": start, "end": end,
            "page": pages[state].ref if state is not None else None,
            "score": round(row[state], 3) if state is not None else 0.0,
            "alternatives": [f"{pages[i].ref} ({row[i]:.2f})" for i in ranked if row[i] > 0],
        })
    spans = []
    for row in rows:
        if spans and spans[-1]["page"] == row["page"]:
            spans[-1]["end"] = row["end"]
            spans[-1]["scores"].append(row["score"])
        else:
            spans.append({"page": row["page"], "start": row["start"], "end": row["end"], "scores": [row["score"]]})
    used = {s["page"] for s in spans}
    return {
        "spans": [{**{k: v for k, v in s.items() if k != "scores"}, "mean_score": round(sum(s["scores"]) / len(s["scores"]), 3)}
                  for s in spans],
        "windows": rows,
        "unmatched_pages": [p.ref for p in pages if p.ref not in used],
    }


def render_markdown(result: dict[str, Any], pages: list[Page]) -> str:
    titles = {p.ref: p.title for p in pages}
    lines = ["# 投影片對應候選（腳本自動比對，需人工確認）", "",
             "分數是逐字稿與該頁文字的 TF-IDF 相似度；< 0.08 代表幾乎沒有共同字詞，請看縮圖判斷。", "",
             "| 時間 | 對應頁 | 頁標題 | 平均分數 |", "| --- | --- | --- | --- |"]
    for span in result["spans"]:
        page = span["page"] or "（無對應投影片）"
        lines.append(f"| {fmt_ts(span['start'])}–{fmt_ts(span['end'])} | {page} | {titles.get(span['page'], '')} | {span['mean_score']} |")
    lines += ["", "## 每分鐘備選", ""]
    lines += [f"- {fmt_ts(w['start'])}: {w['page'] or '—'} ｜備選 {', '.join(w['alternatives']) or '無'}" for w in result["windows"]]
    lines += ["", "## 沒有被對到的頁", "", ", ".join(result["unmatched_pages"]) or "無"]
    return "\n".join(lines) + "\n"
