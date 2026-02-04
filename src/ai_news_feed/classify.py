from typing import Any, Dict, List, Tuple

from .utils import normalize_whitespace


def keyword_score(text: str, keywords: List[str]) -> Tuple[int, List[str]]:
    score = 0
    hits = []
    lower_text = text.lower()
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in lower_text:
            score += 1
            hits.append(kw)
    return score, hits


def fallback_classify(item: Dict[str, Any], content: str, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    title = item.get("title") or ""
    rss_summary = item.get("rss_summary") or ""
    head = content[:2000] if content else ""
    text = normalize_whitespace(f"{title} {rss_summary} {head}")

    best = None
    best_score = -1
    best_hits: List[str] = []

    for cat in taxonomy.get("categories", []):
        keywords = cat.get("keywords", [])
        score_body, hits = keyword_score(text, keywords)
        score_title, hits_title = keyword_score(title, keywords)
        score = score_body + score_title * 2
        hits = list(dict.fromkeys(hits_title + hits))
        if score > best_score:
            best_score = score
            best = cat
            best_hits = hits

    if best is None or best_score <= 0:
        default_id = taxonomy.get("default_category")
        best = next((c for c in taxonomy.get("categories", []) if c.get("id") == default_id), None)
        best_hits = []

    tags = best_hits[:5]
    if len(tags) < 3:
        tags.extend([best.get("name_zh", best.get("id", ""))])
    tags = [t for t in tags if t]
    tags = tags[:5]

    return {
        "summary_bullets_zh": [
            "（关键词兜底）摘要生成失败。",
            "已根据关键词进行初步分类。",
            "建议查看原文以获取更多细节。",
            "该条目可能缺少结构化摘要信息。",
            "如需完整理解请访问原文。",
        ],
        "so_what_zh": "需要进一步人工确认。",
        "primary_category_id": best.get("id"),
        "tags": tags,
        "impact": "Medium",
        "confidence": 0.3,
        "reason": "LLM 失败，采用关键词兜底分类。",
    }
