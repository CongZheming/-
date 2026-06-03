from __future__ import annotations

import logging
import warnings
from collections import defaultdict
from typing import Any, Iterable, Tuple

from modules.rule_config import load_label_options, load_rule_config

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")
    try:
        import jieba
    except ModuleNotFoundError:  # pragma: no cover - exercised only when jieba is unavailable
        jieba = None

if jieba:
    jieba.setLogLevel(logging.WARNING)


LABEL_OPTIONS = load_label_options()
RULE_CONFIG = load_rule_config()

RELEVANCE_LABELS = LABEL_OPTIONS["relevance_label"]
CONTENT_TYPE_LABELS = LABEL_OPTIONS["content_type"]
EMOTION_LABELS = LABEL_OPTIONS["emotion_label"]
FRAME_LABELS = LABEL_OPTIONS["frame_label"]
PLATFORM_ROLE_LABELS = LABEL_OPTIONS["platform_role"]
RESHAPE_TYPE_LABELS = LABEL_OPTIONS["reshape_type"]

RELEVANCE_CORE_KEYWORDS = RULE_CONFIG["relevance"]["core_keywords"]
RELEVANCE_GENERAL_KEYWORDS = RULE_CONFIG["relevance"]["general_keywords"]

KEYWORD_GROUPS = RULE_CONFIG["keyword_groups"]
EMOTION_KEYWORDS = KEYWORD_GROUPS["emotion_label"]
FRAME_KEYWORDS = KEYWORD_GROUPS["frame_label"]
CONTENT_TYPE_KEYWORDS = KEYWORD_GROUPS["content_type"]
RESHAPE_KEYWORDS = KEYWORD_GROUPS["reshape_type"]
PLATFORM_ROLE_KEYWORDS = KEYWORD_GROUPS["platform_role"]

PLATFORM_ROLE_DEFAULTS = RULE_CONFIG.get("platform_role_defaults", {})
SOURCE_TYPE_BOOSTS = RULE_CONFIG.get("source_type_boosts", {})


def _cut_words(text: str) -> list[str]:
    if jieba:
        return jieba.lcut(text or "")
    return list(text or "")


def _count_keyword_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(text.count(keyword) for keyword in keywords if keyword in text)


def _iter_keyword_specs(raw_keywords: Iterable[Any]) -> Iterable[tuple[str, float]]:
    for item in raw_keywords or []:
        if isinstance(item, dict):
            keyword = str(item.get("keyword", "")).strip()
            weight = float(item.get("weight", 1))
        else:
            keyword = str(item).strip()
            weight = 1.0
        if keyword:
            yield keyword, weight


def _keyword_count(text: str, tokens: set[str], keyword: str) -> int:
    direct_count = text.count(keyword)
    if direct_count:
        return direct_count
    return 1 if keyword in tokens else 0


def _score_keyword_list(text: str, keywords: Iterable[str]) -> tuple[int, list[str]]:
    tokens = set(_cut_words(text or ""))
    score = 0
    matched_keywords: list[str] = []
    for keyword in keywords:
        count = _keyword_count(text or "", tokens, keyword)
        if count:
            score += count
            matched_keywords.append(keyword)
    return score, matched_keywords


def _score_labels(text: str, label_keywords: dict[str, list[Any]]) -> tuple[dict[str, float], dict[str, list[str]]]:
    tokens = set(_cut_words(text or ""))
    scores: dict[str, float] = defaultdict(float)
    matched_keywords: dict[str, list[str]] = defaultdict(list)

    for label, keywords in label_keywords.items():
        for keyword, weight in _iter_keyword_specs(keywords):
            count = _keyword_count(text or "", tokens, keyword)
            if not count:
                continue
            scores[label] += count * weight
            if keyword not in matched_keywords[label]:
                matched_keywords[label].append(keyword)

    return dict(scores), dict(matched_keywords)


def _rank_scores(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _make_explanation(
    label: str,
    score: float,
    candidate_scores: dict[str, float],
    candidate_keywords: dict[str, list[str]],
    defaulted: bool = False,
) -> dict[str, Any]:
    return {
        "label": label,
        "score": round(float(score), 3),
        "matched_keywords": candidate_keywords.get(label, []),
        "candidate_scores": {key: round(float(value), 3) for key, value in _rank_scores(candidate_scores)},
        "candidate_keywords": candidate_keywords,
        "defaulted": defaulted,
    }


def _pick_label(
    scores: dict[str, float],
    matched_keywords: dict[str, list[str]],
    default: str,
    mixed_label: str | None = None,
) -> dict[str, Any]:
    if not scores:
        return _make_explanation(default, 0, {}, {}, defaulted=True)

    ranked = _rank_scores(scores)
    label, score = ranked[0]
    if mixed_label and len(ranked) > 1:
        second_label, second_score = ranked[1]
        if score - second_score <= 1 and second_score > 0:
            merged_keywords = {
                **matched_keywords,
                mixed_label: sorted(set(matched_keywords.get(label, []) + matched_keywords.get(second_label, []))),
            }
            return _make_explanation(mixed_label, score + second_score, scores, merged_keywords)

    return _make_explanation(label, score, scores, matched_keywords)


def _classify_relevance_explained(text: str) -> dict[str, Any]:
    core_hits, core_keywords = _score_keyword_list(text or "", RELEVANCE_CORE_KEYWORDS)
    general_hits, general_keywords = _score_keyword_list(text or "", RELEVANCE_GENERAL_KEYWORDS)

    if core_hits >= 2:
        label = "强相关"
    elif core_hits == 1:
        label = "强相关" if general_hits >= 2 else "中等相关"
    elif general_hits >= 3:
        label = "中等相关"
    elif general_hits > 0:
        label = "弱相关"
    else:
        label = "无关"

    score = core_hits * 2 + general_hits
    candidate_scores = {
        "核心词命中": float(core_hits),
        "泛化词命中": float(general_hits),
    }
    candidate_keywords = {label: core_keywords + general_keywords}
    return _make_explanation(label, score, candidate_scores, candidate_keywords, defaulted=score == 0)


def _classify_group_explained(
    text: str,
    label_keywords: dict[str, list[Any]],
    default: str,
    mixed_label: str | None = None,
) -> dict[str, Any]:
    scores, matched_keywords = _score_labels(text or "", label_keywords)
    return _pick_label(scores, matched_keywords, default, mixed_label)


def _classify_platform_role_explained(platform: str, source_type: str, text: str) -> dict[str, Any]:
    scores, matched_keywords = _score_labels(text or "", PLATFORM_ROLE_KEYWORDS)
    for boosted_label, weight in SOURCE_TYPE_BOOSTS.get(source_type, {}).get("platform_role", {}).items():
        scores[boosted_label] = scores.get(boosted_label, 0) + float(weight)
        matched_keywords.setdefault(boosted_label, []).append(f"材料类型:{source_type}")

    default = PLATFORM_ROLE_DEFAULTS.get(platform, "其他")
    return _pick_label(scores, matched_keywords, default)


def _margin_score(candidate_scores: dict[str, float]) -> float:
    values = sorted((float(value) for value in candidate_scores.values()), reverse=True)
    if not values:
        return 0.0
    if len(values) == 1:
        return min(1.0, values[0] / 3)
    top, second = values[0], values[1]
    if top <= 0:
        return 0.0
    return max(0.0, min(1.0, (top - second) / top))


def _calculate_confidence(text: str, explanations: dict[str, dict[str, Any]]) -> tuple[float, bool]:
    evidence_points = sum(float(item.get("score", 0)) for item in explanations.values())
    matched_count = sum(len(item.get("matched_keywords", [])) for item in explanations.values())
    defaulted_count = sum(1 for item in explanations.values() if item.get("defaulted"))

    token_count = max(len(_cut_words(text or "")), 1)
    evidence_score = min(1.0, evidence_points / 18)
    coverage_score = min(1.0, matched_count / min(token_count, 24))
    margin_values = [_margin_score(item.get("candidate_scores", {})) for item in explanations.values()]
    margin_score = sum(margin_values) / max(len(margin_values), 1)

    confidence = 0.25 + evidence_score * 0.4 + margin_score * 0.25 + coverage_score * 0.1
    confidence -= min(0.2, defaulted_count * 0.04)

    if explanations["relevance_label"]["label"] == "无关":
        confidence = min(confidence, 0.45)

    confidence = max(0.2, min(0.95, confidence))
    needs_review = confidence < 0.65 or defaulted_count >= 3 or explanations["emotion_label"]["label"] == "复杂 / 混合"
    return round(confidence, 2), needs_review


def classify_relevance(text: str) -> str:
    return _classify_relevance_explained(text or "")["label"]


def classify_emotion(text: str) -> str:
    return _classify_group_explained(text or "", EMOTION_KEYWORDS, "中立", "复杂 / 混合")["label"]


def classify_frame(text: str) -> str:
    return _classify_group_explained(text or "", FRAME_KEYWORDS, "其他")["label"]


def classify_content_type(text: str) -> str:
    return _classify_group_explained(text or "", CONTENT_TYPE_KEYWORDS, "其他")["label"]


def classify_platform_role(platform: str, source_type: str, text: str) -> str:
    return _classify_platform_role_explained(platform or "", source_type or "", text or "")["label"]


def classify_reshape_type(text: str) -> str:
    return _classify_group_explained(text or "", RESHAPE_KEYWORDS, "其他")["label"]


def classify_all(text: str, platform: str, source_type: str) -> dict[str, Any]:
    text = text or ""
    explanations = {
        "relevance_label": _classify_relevance_explained(text),
        "content_type": _classify_group_explained(text, CONTENT_TYPE_KEYWORDS, "其他"),
        "emotion_label": _classify_group_explained(text, EMOTION_KEYWORDS, "中立", "复杂 / 混合"),
        "frame_label": _classify_group_explained(text, FRAME_KEYWORDS, "其他"),
        "platform_role": _classify_platform_role_explained(platform or "", source_type or "", text),
        "reshape_type": _classify_group_explained(text, RESHAPE_KEYWORDS, "其他"),
    }
    confidence, needs_review = _calculate_confidence(text, explanations)

    return {
        "relevance_label": explanations["relevance_label"]["label"],
        "content_type": explanations["content_type"]["label"],
        "emotion_label": explanations["emotion_label"]["label"],
        "frame_label": explanations["frame_label"]["label"],
        "platform_role": explanations["platform_role"]["label"],
        "reshape_type": explanations["reshape_type"]["label"],
        "confidence": confidence,
        "needs_review": needs_review,
        "explanations": explanations,
    }
