from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import streamlit as st

from database.db_manager import (
    delete_classification,
    delete_material,
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
from modules.ocr_processor import extract_ocr_result_from_image
from modules.rule_classifier import LABEL_OPTIONS, classify_all
from modules.text_cleaner import clean_text
from modules.utils import SCREENSHOTS_DIR, ensure_dirs, generate_id, get_current_time


PLATFORMS = ["微博", "小红书", "知乎", "豆瓣", "抖音", "其他"]
SOURCE_TYPES = ["帖文", "评论", "转发", "观察记录", "访谈摘录"]
INPUT_METHODS = {"文本粘贴": "text", "截图上传": "screenshot"}
CLASSIFICATION_FIELDS = [
    ("relevance_label", "议题相关性"),
    ("content_type", "内容类型"),
    ("emotion_label", "情绪标签"),
    ("frame_label", "话语框架"),
    ("platform_role", "平台角色"),
    ("reshape_type", "议题重塑类型"),
]


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


def _load_explanations(value) -> dict:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if pd.isna(value):
        return {}
    if not value:
        return {}
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _display_explanations(explanations: dict) -> None:
    if not explanations:
        return
    with st.expander("规则命中证据", expanded=False):
        for field, label_text in CLASSIFICATION_FIELDS:
            detail = explanations.get(field, {})
            matched = detail.get("matched_keywords") or []
            candidate_scores = detail.get("candidate_scores") or {}
            st.markdown(f"**{label_text}：{detail.get('label', '未知')}**")
            st.caption(f"分数：{detail.get('score', 0)}；命中词：{'、'.join(matched) if matched else '无'}")
            if candidate_scores:
                st.json(candidate_scores, expanded=False)


def _display_classification_result(result: dict) -> None:
    rows = []
    for field, label_text in CLASSIFICATION_FIELDS:
        rows.append({"维度": label_text, "推荐标签": result.get(field)})
    rows.append({"维度": "置信度", "推荐标签": result.get("confidence")})
    rows.append({"维度": "需要复核", "推荐标签": "是" if result.get("needs_review") else "否"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    _display_explanations(result.get("explanations", {}))


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
            ocr_result = extract_ocr_result_from_image(screenshot_path)
            raw_text = ocr_result.text
            if ocr_result.success:
                if ocr_result.confidence is not None:
                    st.caption(f"OCR 平均置信度：{ocr_result.confidence}")
            else:
                st.info(f"{ocr_result.error or 'OCR 暂不可用'}。请在下方手动补充文本。")
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
    _display_classification_result(result)

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
                    "needs_review": "是" if row.get("needs_review") else "否",
                }
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    _display_explanations(_load_explanations(row.get("explanation_json")))

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


def _format_option(row: pd.Series, id_column: str) -> str:
    platform = row.get("platform") or "未知平台"
    source_type = row.get("source_type") or "未知类型"
    keyword = row.get("keyword") or "无关键词"
    return f"{row[id_column]} | {platform} | {source_type} | {keyword}"


def page_delete() -> None:
    st.header("数据删除")
    delete_message = st.session_state.pop("delete_message", None)
    if delete_message:
        st.success(delete_message)
    st.warning("删除操作不可撤销。建议先在“数据导出”页面导出备份，再删除误录数据。")

    material_tab, classification_tab = st.tabs(["删除材料", "删除分类记录"])

    with material_tab:
        materials = load_materials()
        if materials.empty:
            st.info("暂无可删除材料。")
        else:
            material_options = [_format_option(row, "material_id") for _, row in materials.iterrows()]
            selected = st.selectbox("选择要删除的材料", material_options)
            material_id = selected.split(" | ")[0]
            selected_row = materials[materials["material_id"] == material_id].iloc[0]

            st.text_area("原文预览", selected_row.get("raw_text") or "", height=140, disabled=True)
            st.text_area("清洗文本预览", selected_row.get("clean_text") or "", height=140, disabled=True)

            delete_screenshot_file = st.checkbox("同时删除 data/screenshots/ 下对应截图文件", value=False)
            confirm_material_id = st.text_input("请输入 material_id 确认删除", key="confirm_material_id")
            if st.button("删除该材料及其关联记录", type="primary"):
                if confirm_material_id != material_id:
                    st.error("确认 ID 不一致，未执行删除。")
                    return
                result = delete_material(material_id, delete_screenshot_file=delete_screenshot_file)
                if result.get("deleted"):
                    removed = "，截图文件已删除" if result.get("screenshot_file_removed") else ""
                    st.session_state["delete_message"] = f"已删除材料 {material_id} 及其关联 OCR / 分类记录{removed}。"
                    st.rerun()
                else:
                    st.error(f"删除失败：{result.get('message', '未知错误')}")

    with classification_tab:
        classifications = load_joined_dataset()
        classifications = classifications[classifications["classification_id"].notna()] if not classifications.empty else classifications
        if classifications.empty:
            st.info("暂无可删除分类记录。")
        else:
            classification_options = [_format_option(row, "classification_id") for _, row in classifications.iterrows()]
            selected = st.selectbox("选择要删除的分类记录", classification_options)
            classification_id = selected.split(" | ")[0]
            selected_row = classifications[classifications["classification_id"] == classification_id].iloc[0]

            st.write(
                {
                    "material_id": selected_row.get("material_id"),
                    "relevance_label": selected_row.get("relevance_label"),
                    "emotion_label": selected_row.get("emotion_label"),
                    "frame_label": selected_row.get("frame_label"),
                    "reshape_type": selected_row.get("reshape_type"),
                }
            )
            st.caption("只删除分类记录不会删除原始材料；该材料会重新出现在“自动识别与归类”的未分类队列中。")
            confirm_classification_id = st.text_input("请输入 classification_id 确认删除", key="confirm_classification_id")
            if st.button("仅删除该分类记录", type="primary"):
                if confirm_classification_id != classification_id:
                    st.error("确认 ID 不一致，未执行删除。")
                    return
                deleted_count = delete_classification(classification_id)
                if deleted_count:
                    st.session_state["delete_message"] = f"已删除分类记录 {classification_id}。"
                    st.rerun()
                else:
                    st.error("未找到该分类记录，删除失败。")


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
        ["材料上传 / 文本录入", "自动识别与归类", "人工复核", "数据浏览", "数据删除", "数据导出", "统计概览"],
    )

    if page == "材料上传 / 文本录入":
        page_input()
    elif page == "自动识别与归类":
        page_classify()
    elif page == "人工复核":
        page_review()
    elif page == "数据浏览":
        page_browse()
    elif page == "数据删除":
        page_delete()
    elif page == "数据导出":
        page_export()
    else:
        page_stats()


if __name__ == "__main__":
    main()
