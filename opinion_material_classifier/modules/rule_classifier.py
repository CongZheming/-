from __future__ import annotations

import warnings
from collections import Counter
import logging
from typing import Dict, Iterable, Tuple

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="pkg_resources is deprecated as an API.*",
        category=UserWarning,
    )
    import jieba

jieba.setLogLevel(logging.WARNING)


RELEVANCE_CORE_KEYWORDS = [
    "生育",
    "生孩子",
    "三孩",
    "二孩",
    "四孩",
    "生育政策",
    "鼓励生育",
    "生育意愿",
    "生育风险",
    "女性生育",
    "人口出生率",
    "专家称生育三到四子女死亡风险最低",
    "不婚不育",
    "催生",
    "育儿",
    "养孩子",
]

RELEVANCE_GENERAL_KEYWORDS = ["孩子", "家庭", "压力", "结婚", "婚姻", "父母", "教育", "人口"]

EMOTION_KEYWORDS = {
    "焦虑": ["压力", "焦虑", "养不起", "不敢生", "负担", "房贷", "教育", "成本"],
    "愤怒": ["离谱", "恶心", "凭什么", "荒唐", "气死", "无语", "反感"],
    "无奈": ["没办法", "算了", "现实", "普通人", "不容易"],
    "嘲讽": ["砖家", "专家自己生", "建议专家", "笑死", "哈哈", "典", "绷不住"],
    "理性分析": ["数据", "样本", "研究", "变量", "论文", "结论", "方法", "统计"],
    "支持": ["支持", "应该鼓励", "有必要", "可以考虑"],
    "反对": ["反对", "不支持", "不可能", "不想生", "不愿意"],
    "恐惧": ["害怕", "恐惧", "死亡", "风险", "不敢", "危险"],
    "调侃": ["段子", "哈哈哈", "乐", "梗", "表情包"],
}

FRAME_KEYWORDS = {
    "生育成本": ["房贷", "车贷", "养不起", "奶粉", "教育", "补课", "托育", "成本", "压力", "钱"],
    "女性身体风险": ["怀孕", "生产", "死亡率", "身体", "子宫", "产后", "健康", "风险", "痛"],
    "性别不平等": ["女性", "男性", "妈妈", "爸爸", "牺牲", "家务", "职场", "产假", "歧视"],
    "专家权威质疑": ["专家", "教授", "研究", "数据", "样本", "论文", "结论", "调查", "科学"],
    "政策质疑": ["政策", "配套", "补贴", "托育", "保障", "落实", "宣传", "口号"],
    "政策信任": ["支持政策", "相信政策", "政策解释", "配套完善", "鼓励"],
    "婚恋压力": ["结婚", "婚姻", "彩礼", "伴侣", "对象", "婚恋"],
    "家庭责任": ["家庭", "父母", "老人", "照顾", "责任", "家里"],
    "职场歧视": ["就业", "公司", "产假", "升职", "辞退", "职场"],
    "育儿资源": ["幼儿园", "托育", "学位", "医疗", "奶粉", "补课", "教育资源"],
    "人口焦虑": ["人口", "出生率", "老龄化", "少子化", "人口危机"],
    "代际观念": ["父母", "长辈", "上一代", "年轻人", "观念"],
    "媒体标题党": ["标题", "热搜", "带节奏", "断章取义", "媒体"],
    "平台审核规避": ["谐音", "缩写", "图中图", "夹", "审核", "限流", "删帖"],
    "科学研究方法质疑": ["方法", "变量", "样本", "统计", "模型", "因果"],
    "个人经验叙事": ["我", "本人", "身边", "朋友", "经历", "亲身", "家里"],
}

CONTENT_TYPE_KEYWORDS = {
    "政策讨论": ["政策", "补贴", "托育", "保障", "人口", "出生率"],
    "专家质疑": ["专家", "教授", "砖家", "研究", "论文", "样本", "结论"],
    "个人经验": ["我", "本人", "身边", "朋友", "经历", "亲身", "家里"],
    "情绪宣泄": ["离谱", "恶心", "气死", "无语", "焦虑", "害怕", "反感"],
    "反讽调侃": ["建议专家", "砖家", "笑死", "哈哈", "典", "绷不住", "段子"],
    "理性分析": ["数据", "样本", "变量", "论文", "统计", "方法"],
    "平台审核规避": ["谐音", "缩写", "图中图", "审核", "限流", "删帖"],
    "二次创作": ["梗", "表情包", "视频", "剪辑", "段子"],
    "媒体传播": ["媒体", "热搜", "标题", "新闻", "词条"],
}

RESHAPE_KEYWORDS = {
    "标题化": ["热搜", "标题", "词条", "媒体", "新闻"],
    "情绪化": ["离谱", "焦虑", "愤怒", "害怕", "反感", "恶心"],
    "经验化": ["我", "身边", "朋友", "经历", "真实", "亲身"],
    "性别化": ["女性", "男性", "妈妈", "爸爸", "性别", "女的", "男的"],
    "娱乐化": ["梗", "哈哈", "笑死", "段子", "表情包"],
    "专业化": ["数据", "样本", "方法", "变量", "论文", "研究"],
    "政策化": ["政策", "国家", "补贴", "托育", "保障", "人口"],
    "道德化": ["责任", "义务", "孝顺", "自私", "道德", "应该"],
    "反讽化": ["建议专家", "砖家", "自己生", "典", "绷不住"],
    "审核规避化": ["谐音", "缩写", "图中图", "夹", "限流", "删帖"],
}

PLATFORM_ROLE_DEFAULTS = {
    "微博": "热度扩散",
    "小红书": "经验分享",
    "知乎": "理性沉淀",
    "豆瓣": "情绪发酵",
    "抖音": "二次创作",
}


def _count_keyword_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(text.count(keyword) for keyword in keywords if keyword in text)


def _score_labels(text: str, label_keywords: Dict[str, list[str]]) -> Counter:
    tokens = set(jieba.lcut(text))
    scores: Counter = Counter()
    for label, keywords in label_keywords.items():
        for keyword in keywords:
            if keyword in text or keyword in tokens:
                scores[label] += text.count(keyword) if keyword in text else 1
    return scores


def _pick_label(scores: Counter, default: str, mixed_label: str | None = None) -> Tuple[str, int]:
    if not scores:
        return default, 0
    ranked = scores.most_common()
    if mixed_label and len(ranked) > 1 and ranked[0][1] - ranked[1][1] <= 1 and ranked[1][1] > 0:
        return mixed_label, ranked[0][1] + ranked[1][1]
    return ranked[0][0], ranked[0][1]


def classify_relevance(text: str) -> str:
    core_hits = _count_keyword_hits(text, RELEVANCE_CORE_KEYWORDS)
    general_hits = _count_keyword_hits(text, RELEVANCE_GENERAL_KEYWORDS)

    if core_hits >= 2:
        return "强相关"
    if core_hits == 1:
        return "强相关" if general_hits >= 2 else "中等相关"
    if general_hits >= 3:
        return "中等相关"
    if general_hits > 0:
        return "弱相关"
    return "无关"


def classify_emotion(text: str) -> str:
    label, _ = _pick_label(_score_labels(text, EMOTION_KEYWORDS), "中立", "复杂 / 混合")
    return label


def classify_frame(text: str) -> str:
    label, _ = _pick_label(_score_labels(text, FRAME_KEYWORDS), "其他")
    return label


def classify_content_type(text: str) -> str:
    label, _ = _pick_label(_score_labels(text, CONTENT_TYPE_KEYWORDS), "其他")
    return label


def classify_platform_role(platform: str, source_type: str, text: str) -> str:
    scores = _score_labels(
        text,
        {
            "话题定义": ["热搜", "词条", "标题", "话题"],
            "热度扩散": ["转发", "评论", "热搜", "扩散"],
            "情绪发酵": ["离谱", "焦虑", "愤怒", "反感", "无语"],
            "经验分享": ["我", "本人", "经历", "亲身", "身边", "真实"],
            "理性沉淀": ["数据", "样本", "论文", "研究", "方法", "统计"],
            "二次创作": ["视频", "剪辑", "表情包", "段子", "梗"],
            "梗文化生成": ["梗", "笑死", "哈哈", "典", "绷不住"],
            "政策解释": ["政策", "解释", "配套", "补贴", "保障"],
            "反讽抵抗": ["建议专家", "砖家", "自己生", "反讽"],
            "审核规避": ["谐音", "缩写", "图中图", "限流", "删帖", "审核"],
        },
    )
    if source_type == "转发":
        scores["热度扩散"] += 1
    label, _ = _pick_label(scores, PLATFORM_ROLE_DEFAULTS.get(platform, "其他"))
    if platform == "豆瓣" and label == "其他":
        return "情绪发酵"
    return label


def classify_reshape_type(text: str) -> str:
    label, _ = _pick_label(_score_labels(text, RESHAPE_KEYWORDS), "其他")
    return label


def classify_all(text: str, platform: str, source_type: str) -> dict:
    text = text or ""
    scores = [
        _count_keyword_hits(text, RELEVANCE_CORE_KEYWORDS),
        sum(_score_labels(text, EMOTION_KEYWORDS).values()),
        sum(_score_labels(text, FRAME_KEYWORDS).values()),
        sum(_score_labels(text, CONTENT_TYPE_KEYWORDS).values()),
        sum(_score_labels(text, RESHAPE_KEYWORDS).values()),
    ]
    hit_count = sum(scores)
    confidence = min(0.95, 0.35 + hit_count * 0.05)
    if classify_relevance(text) == "无关":
        confidence = min(confidence, 0.45)

    return {
        "relevance_label": classify_relevance(text),
        "content_type": classify_content_type(text),
        "emotion_label": classify_emotion(text),
        "frame_label": classify_frame(text),
        "platform_role": classify_platform_role(platform, source_type, text),
        "reshape_type": classify_reshape_type(text),
        "confidence": round(confidence, 2),
    }
