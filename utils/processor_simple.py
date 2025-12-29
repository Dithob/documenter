"""
docling_processor_minimal.py

极简版 Docling 文档处理器（中文注释）：
- 直接对 URL 或本地路径调用 DocumentConverter.convert()
- 导出 Markdown、JSON，并对分块做最小化序列化
- 最少参数、最少步骤，便于集成
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker import HierarchicalChunker

# 简单日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("docling_minimal")


def create_converter(artifacts_path: str, ocr_engine: str = "auto", enable_remote_services: bool = False) -> DocumentConverter:
    """
    创建最小化的 DocumentConverter。
    artifacts_path: 本地模型目录（或空字符串让 Docling 使用默认）
    ocr_engine: "auto" | "easyocr" | "tesseract" | "none"
    """
    opts = {"artifacts_path": artifacts_path} if artifacts_path else {}
    oe = (ocr_engine or "auto").lower()
    if oe == "easyocr":
        opts.update({"do_ocr": True, "ocr_options": EasyOcrOptions()})
    elif oe == "tesseract":
        opts.update({"do_ocr": True, "ocr_options": TesseractOcrOptions()})
    elif oe == "none":
        opts["do_ocr"] = False
    if enable_remote_services:
        opts["enable_remote_services"] = True

    pipeline_opts = PdfPipelineOptions(**opts)
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)})
    return converter


def _serialize_chunk(c) -> Any:
    """简易把 chunk 转成可序列化形式：优先 to_dict，否则用 repr。"""
    if hasattr(c, "to_dict"):
        try:
            return c.to_dict()
        except Exception:
            pass
    return repr(c)


def process_document(
    source: str,
    artifacts_path: str,
    *,
    ocr_engine: str = "auto",
    enable_remote_services: bool = False,
    max_num_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    极简主函数：处理 source（URL 或本地路径），返回结果字典：
    { "source", "input_used", "markdown", "json", "chunks", "meta" }
    """
    logger.info("开始处理：%s", source)
    converter = create_converter(artifacts_path, ocr_engine=ocr_engine, enable_remote_services=enable_remote_services)

    kwargs = {}
    if max_num_pages:
        kwargs["max_num_pages"] = max_num_pages

    # 直接把 source 交给 docling（支持 URL 或本地路径）
    result = converter.convert(str(source), **kwargs)

    md = result.document.export_to_markdown()
    # export_to_json 可能返回 dict/list；优先用它
    json_obj = None
    if hasattr(result.document, "export_to_json"):
        try:
            json_obj = result.document.export_to_json()
        except Exception:
            json_obj = None
    if json_obj is None and hasattr(result.document, "export_to_dict"):
        try:
            json_obj = result.document.export_to_dict()
        except Exception:
            json_obj = None
    if json_obj is None:
        json_obj = {"note": "unserializable_document"}

    raw_chunks = list(HierarchicalChunker().chunk(result.document))
    chunks = [_serialize_chunk(c) for c in raw_chunks]

    out = {
        "source": source,
        "input_used": source,
        "markdown": md,
        "json": json_obj,
        "chunks": chunks,
        "meta": {"pages_processed": getattr(result, "pages_processed", None)},
    }
    logger.info("处理完成：%s (pages_processed=%s)", source, out["meta"]["pages_processed"])
    return out


def save_outputs(out: Dict[str, Any], out_dir: str, basename: str = "doc"):
    """
    将结果保存为：
      - {basename}.md
      - {basename}.json
      - {basename}_chunks.json
    """
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{basename}.md").write_text(out.get("markdown", ""), encoding="utf-8")
    # 将 json 对象序列化为字符串（确保中文不转义）
    (p / f"{basename}.json").write_text(json.dumps(out.get("json", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    (p / f"{basename}_chunks.json").write_text(json.dumps(out.get("chunks", []), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已保存到目录：%s", p.resolve())


# ----------------- 最小示例 -----------------
if __name__ == "__main__":
    ARTIFACTS = r"C:\Users\zmn\.cache\docling\models"  # 修改为你的模型路径或置空
    OUTDIR = "result_minimal"

    # 直接处理远程 PDF（Docling 会内部下载）
    url = "https://arxiv.org/pdf/2408.09869.pdf"
    try:
        res = process_document(url, ARTIFACTS, ocr_engine="auto", max_num_pages=5)
        save_outputs(res, OUTDIR, "simple_pdf")
    except Exception as e:
        logger.exception("处理失败：%s", e)
