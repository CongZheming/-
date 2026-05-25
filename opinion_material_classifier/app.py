from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from database.db_manager import (
    export_all,
    get_latest_unclassified_material,
    get_unchecked_classifications,
    init_database,
    insert_classification,
    insert_material,
    insert_ocr_result,
    load_classifications,
    load_joined_dataset,
    load_materials,
    update_human_review,
)
from modules.ocr_processor import extract_text_from_image
from modules.rule_classifier import LABEL_OPTIONS, classify_all
from modules.text_cleaner import clean_text
from modules.utils import SCREENSHOTS_DIR, ensure_dirs, generate_id, get_current_time


PLATFORMS = ["微博", "小红书", "知乎", "豆瓣", "抖音", "其他"]
SOURCE_TYPES = ["帖文", "评论", "转发", "观察记录", "访谈摘录"]
INPUT_METHODS = {"文本粘贴": "text", "截图上传": "screenshot"}


def bootstrap() -> None:
    ensure_dirs()
    init_database()


def save_uploaded_screenshot(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix or ".png"
    output_path = SCREENSHOTS_DIR / f"{generate_id('screenshot')}{suffix}"
    with output_path.open("wb") as file:
        shutil.copyfileobj(uploaded_file, file)
    return str(output_path)


def build_classification(material: dict) -> dict:
    result = classify_all(material["clean_text"], material["platform"], material["source_type"])
    return {
        "classification_id": generate_id("cls"),
        "material_id": material["material_id"],
        **result,
        "classified_time": get_current_time(),
    }


def page_input() -> None:
    st.header("材料上传 / 文本录入")
    platform = st.selectbox("平台", PLATFORMS)
    source_type = st.selectbox("材料类型", SOURCE_TYPES)
    input_label = st.radio("输入方式", list(INPUT_METHODS.keys()), horizontal=True)
    keyword = st.text_input("关键词")
    url = st.text_input("原始链接（可选）")
    researcher_note = st.text_area("研究者备注（可选）", height=80)

    screenshot_path = ""
    raw_text = ""
    if INPUT_METHODS[input_label] == "text":
        raw_text = st.text_area("原始文本", height=220, placeholder="粘贴帖文、评论、转发内容或观察记录。")
    else:
        uploaded_file = st.file_uploader("上传截图", type=["png", "jpg", "jpeg", "webp"])
        if uploaded_file:
            screenshot_path = save_uploaded_screenshot(uploaded_file)
            raw_text = extract_text_from_image(screenshot_path)
            if not raw_text:
                st.info("未检测到可用 OCR 依赖或识别结果为空，请在下方手动补充文本。")
            raw_text = st.text_area("OCR 识别文本 / 手动修正文本", value=raw_text, height=220)

    cleaned = clean_text(raw_text)
    st.subheader("清洗后文本")
    st.text_area("clean_text", value=cleaned, height=160, disabled=True, label_visibility="collapsed")

    if st.button("保存并进行分类", type="primary"):
        if not cleaned:
            st.warning("请先输入或识别出有效文本。")
            return
        material_id = generate_id("mat")
        material = {
            "material_id": material_id,
            "platform": platform,
            "source_type": source_type,
            "keyword": keyword,
            "url": url,
            "raw_text": raw_text,
            "clean_text": cleaned,
            "screenshot_path": screenshot_path,
            "input_method": INPUT_METHODS[input_label],
            "upload_time": get_current_time(),
            "researcher_note": researcher_note,
        }
        insert_material(material)
        if screenshot_path:
            insert_ocr_result(
                {
                    "ocr_id": generate_id("ocr"),
                    "material_id": material_id,
                    "original_image_path": screenshot_path,
                    "recognized_text": raw_text,
                    "corrected_text": raw_text,
                    "ocr_time": get_current_time(),
                }
            )
        st.success(f"材料已保存：{material_id}。请进入“自动识别与归类”保存推荐分类。")


def page_classify() -> None:
    st.header("自动识别与归类")
    material = get_latest_unclassified_material()
    if not material:
        st.info("暂无未分类材料。")
        return

    st.caption(f"{material['platform']} / {material['source_type']} / {material['upload_time']}")
    st.text_area("原文", material["raw_text"] or "", height=160)
    st.text_area("清洗文本", material["clean_text"] or "", height=160)

    result = classify_all(material["clean_text"] or "", material["platform"] or "", material["source_type"] or "")
    st.subheader("系统推荐标签")
    st.json(result, expanded=True)

    if st.button("保存推荐分类结果", type="primary"):
        insert_classification(
            {
                "classification_id": generate_id("cls"),
                "material_id": material["material_id"],
                **result,
                "classified_time": get_current_time(),
            }
        )
        st.success("推荐分类结果已保存，可进入“人工复核”确认最终标签。")


def page_review() -> None:
    st.header("人工复核")
    df = get_unchecked_classifications()
    if df.empty:
        st.info("暂无待复核分类记录。")
        return

    row_options = [f"{row.classification_id} | {row.platform} | {row.keyword or '无关键词'}" for row in df.itertuples()]
    selected = st.selectbox("待复核记录", row_options)
    classification_id = selected.split(" | ")[0]
    row = df[df["classification_id"] == classification_id].iloc[0]

    st.text_area("原文", row["raw_text"] or "", height=140)
    st.text_area("清洗文本", row["clean_text"] or "", height=140)
    st.write("系统推荐：")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "relevance_label": row["relevance_label"],
                    "content_type": row["content_type"],
                    "emotion_label": row["emotion_label"],
                    "frame_label": row["frame_label"],
                    "platform_role": row["platform_role"],
                    "reshape_type": row["reshape_type"],
                    "confidence": row["confidence"],
                }
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    final_labels = {}
    for field, label in [
        ("final_relevance_label", "最终议题相关性"),
        ("final_content_type", "最终内容类型"),
        ("final_emotion_label", "最终情绪标签"),
        ("final_frame_label", "最终话语框架"),
        ("final_platform_role", "最终平台角色"),
        ("final_reshape_type", "最终议题重塑类型"),
    ]:
        base_field = field.replace("final_", "")
        options = LABEL_OPTIONS[base_field]
        current = row[field] if pd.notna(row.get(field)) and row.get(field) else row[base_field]
        index = options.index(current) if current in options else 0
        final_labels[field] = st.selectbox(label, options, index=index)

    if st.button("确认复核并保存", type="primary"):
        update_human_review(classification_id, final_labels)
        st.success("人工复核结果已保存。")


def page_browse() -> None:
    st.header("数据浏览")
    joined = load_joined_dataset()

    if not joined.empty:
        col1, col2, col3, col4 = st.columns(4)
        platform = col1.selectbox("筛选平台", ["全部"] + sorted(joined["platform"].dropna().unique().tolist()))
        source_type = col2.selectbox("筛选类型", ["全部"] + sorted(joined["source_type"].dropna().unique().tolist()))
        emotion = col3.selectbox("筛选情绪", ["全部"] + sorted(joined["final_emotion_label"].dropna().unique().tolist()))
        frame = col4.selectbox("筛选框架", ["全部"] + sorted(joined["final_frame_label"].dropna().unique().tolist()))
        filtered = joined.copy()
        if platform != "全部":
            filtered = filtered[filtered["platform"] == platform]
        if source_type != "全部":
            filtered = filtered[filtered["source_type"] == source_type]
        if emotion != "全部":
            filtered = filtered[filtered["final_emotion_label"] == emotion]
        if frame != "全部":
            filtered = filtered[filtered["final_frame_label"] == frame]
        st.subheader("筛选后的合并数据")
        st.dataframe(filtered, hide_index=True, use_container_width=True)

    st.subheader("materials 表")
    st.dataframe(load_materials(), hide_index=True, use_container_width=True)
    st.subheader("classifications 表")
    st.dataframe(load_classifications(), hide_index=True, use_container_width=True)


def page_export() -> None:
    st.header("数据导出")
    st.write("导出文件将保存到 `data/output/`。")
    if st.button("导出 Excel / CSV", type="primary"):
        paths = export_all()
        st.success("导出完成。")
        for name, path in paths.items():
            st.write(f"{name}: `{path}`")


def chart_counts(df: pd.DataFrame, column: str, title: str) -> None:
    st.subheader(title)
    if df.empty or column not in df.columns:
        st.info("暂无数据。")
        return
    counts = df[column].fillna("未分类").value_counts()
    if counts.empty:
        st.info("暂无数据。")
    else:
        st.bar_chart(counts)


def page_stats() -> None:
    st.header("统计概览")
    df = load_joined_dataset()
    chart_counts(df, "platform", "各平台材料数量")
    chart_counts(df, "source_type", "各材料类型数量")
    chart_counts(df, "final_emotion_label", "各情绪标签数量")
    chart_counts(df, "final_frame_label", "各话语框架数量")
    chart_counts(df, "final_reshape_type", "各议题重塑类型数量")


def main() -> None:
    st.set_page_config(page_title="跨平台舆情材料识别与归类系统", layout="wide")
    bootstrap()
    st.title("跨平台舆情材料识别与归类系统")
    page = st.sidebar.radio(
        "导航",
        ["材料上传 / 文本录入", "自动识别与归类", "人工复核", "数据浏览", "数据导出", "统计概览"],
    )

    if page == "材料上传 / 文本录入":
        page_input()
    elif page == "自动识别与归类":
        page_classify()
    elif page == "人工复核":
        page_review()
    elif page == "数据浏览":
        page_browse()
    elif page == "数据导出":
        page_export()
    else:
        page_stats()


if __name__ == "__main__":
    main()
