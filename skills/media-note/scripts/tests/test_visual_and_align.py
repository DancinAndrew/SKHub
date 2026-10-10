from medianote_lib import align, frames, pdfpages
from medianote_lib.common import Segment


def test_find_holds_returns_still_runs():
    diffs = [0, 3, 50, 2, 4, 60, 70, 1]
    assert frames.find_holds(diffs) == [[0, 1], [2, 3, 4], [6, 7]]
    assert frames.find_holds([0, 99, 99]) == []


def test_recurring_members_needs_many_spread_out_repeats():
    host = 0
    chart = (1 << 20) - 1  # 20 bits away from host
    reps = [0, 30, 60, 90, 45]
    hashes = {0: host, 30: host, 60: host, 90: host, 45: chart}
    assert frames.recurring_members(reps, hashes, total_frames=100) == {0, 30, 60, 90}
    assert frames.recurring_members([0, 5, 10, 15], {0: host, 5: host, 10: host, 15: host}, total_frames=100) == set()


def test_dedupe_keeps_latest_of_near_twins_in_time_order():
    a, a2, b = 0, 0b1, (1 << 64) - 1
    reps = [10, 20, 30, 40]
    hashes = {10: a, 20: b, 30: a2, 40: b}
    assert frames.dedupe(reps, hashes, skip=set()) == [30, 40]
    assert frames.dedupe(reps, hashes, skip={20, 40}) == [30]


def test_tokenize_mixes_english_years_and_cjk_bigrams():
    tokens = align.tokenize("The Neural Networks of 2012 講深度學習")
    assert {"neural", "network", "2012", "深度", "學習"} <= set(tokens)
    assert "the" not in tokens and "of" not in tokens


def test_viterbi_prefers_forward_path_and_null_for_silence():
    silence = [0.0, 0.0, 0.0]
    scores = [[0.6, 0.1, 0.0], [0.2, 0.5, 0.1], silence, silence, silence, [0.1, 0.1, 0.7]]
    assert align.viterbi(scores) == [0, 1, None, None, None, 2]
    one_quiet_minute = [[0.6, 0.1, 0.0], [0.2, 0.5, 0.1], silence, [0.1, 0.1, 0.7]]
    assert align.viterbi(one_quiet_minute)[2] is not None
    assert align.viterbi([]) == []


def test_align_maps_windows_to_matching_pages():
    pages = [
        align.Page("D1", 1, "Supervised Learning", "labels classification regression"),
        align.Page("D1", 2, "Clustering", "unsupervised clustering kmeans groups"),
        align.Page("D1", 3, "Reinforcement", "reward agent policy environment"),
    ]
    segs = [
        Segment(5, 20, "supervised learning uses labels for classification and regression"),
        Segment(65, 80, "clustering is unsupervised, kmeans finds groups"),
        Segment(125, 140, "the agent gets a reward from the environment and learns a policy"),
    ]
    result = align.align(segs, pages)
    assert [s["page"] for s in result["spans"]] == ["D1 p.1", "D1 p.2", "D1 p.3"]
    assert result["unmatched_pages"] == []
    assert "D1 p.2" in align.render_markdown(result, pages)


def test_pdf_text_helpers():
    assert pdfpages.split_pages("a\fb  c\f", 3) == ["a", "b c", ""]
    assert pdfpages.page_title("\n 12 \n  Story of ML  \nbody") == "Story of ML"
    pages = [{"text": "Machine Learning and GAN. Machine Learning again"}, {"text": "GAN and Deep Learning"}]
    terms = pdfpages.key_terms(pages)
    assert terms[0] == "GAN"  # ranked by number of pages mentioning the term
    assert "Machine Learning" in terms and "Deep Learning" in terms
