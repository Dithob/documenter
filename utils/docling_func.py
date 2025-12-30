import os
import requests
import logging
import mimetypes
import urllib.parse
from typing import Optional, Union, Dict
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TesseractOcrOptions,
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker import HierarchicalChunker


# ---------------- 日志配置 ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("docling_processor_final")


# ----------------- 独立的类型获取函数 -----------------
def _strip_mime(ct: Optional[str]) -> Optional[str]:
    if not ct:
        return None
    return ct.split(";")[0].strip().lower()

def get_content_type_from_source(source: str, timeout: int = 6, user_agent: str = "docling/auto/1.0") -> Dict[str, Optional[str]]:
    """
    简化版：根据 source（URL、本地路径或 data URI）返回 {'mime','ext','source_type'}。
    不依赖额外库（不使用 python-magic）。
    """
    result = {"mime": None, "ext": None, "source_type": "unknown"}
    parsed = urllib.parse.urlparse(source)

    # 1) data URI
    if parsed.scheme == "data":
        header = source.split(",", 1)[0]
        mediatype = header[5:] if header.startswith("data:") else ""
        mime = _strip_mime(mediatype.split(";")[0]) or "text/plain"
        ext = mimetypes.guess_extension(mime) or None
        return {"mime": mime, "ext": ext, "source_type": "data"}

    # 2) local file (file:// or plain path that exists)
    if parsed.scheme == "file":
        local = urllib.parse.unquote(parsed.path)
    else:
        local = source if os.path.exists(source) else None

    if local:
        result["source_type"] = "local"
        mime, _ = mimetypes.guess_type(local)
        result["mime"] = _strip_mime(mime)
        result["ext"] = os.path.splitext(local)[1].lower() or None
        return result

    # 3) URL (http/https/ftp)
    if parsed.scheme in ("http", "https", "ftp"):
        result["source_type"] = "url"
        path_ext = os.path.splitext(parsed.path.split("?")[0])[1].lower()
        if path_ext:
            # 如果 URL 带扩展名，先用扩展名推断 mime
            mime_guess = mimetypes.types_map.get(path_ext) or mimetypes.guess_type("file"+path_ext)[0]
            result["ext"] = path_ext
            result["mime"] = _strip_mime(mime_guess)
            # 如果能猜到 mime 就返回
            if result["mime"]:
                return result

        headers = {"User-Agent": user_agent, "Accept": "*/*"}
        # 尝试 HEAD
        try:
            r = requests.head(source, allow_redirects=True, timeout=timeout, headers=headers)
            ct = _strip_mime(r.headers.get("Content-Type"))
            r.close()
            if ct:
                result["mime"] = ct
                if not result["ext"]:
                    result["ext"] = mimetypes.guess_extension(ct)
                return result
        except requests.RequestException:
            pass

        # HEAD 失败或无 Content-Type，尝试 GET(stream) 只读 headers
        try:
            r = requests.get(source, stream=True, allow_redirects=True, timeout=timeout, headers=headers)
            ct = _strip_mime(r.headers.get("Content-Type"))
            r.close()
            if ct:
                result["mime"] = ct
                if not result["ext"]:
                    result["ext"] = mimetypes.guess_extension(ct)
                return result
        except requests.RequestException:
            pass

        return result

    # 其它情况返回尽量的信息（可能为空）
    return result


def process_document(
        source: str,
        artifacts_path: str,
        do_ocr: bool = False,
        ocr_engine: str = "easyocr",
        max_num_pages: int = 100,
        max_file_size: int = 20 * 1024 * 1024,  # 20 MB
        enable_chunk: bool = True
):
    """
    处理文档/图片/表格并返回结构化内容
    返回内容根据类型：
      - Excel -> HTML
      - 图片 -> HTML（或 Markdown）
      - 其他（PDF/文档等） -> Markdown
    """
    # ——— 配置 OCR Options ———
    ocr_options = None
    if do_ocr:
        if ocr_engine.lower() == "tesseract":
            ocr_options = TesseractOcrOptions()
        else:
            ocr_options = EasyOcrOptions()

    # ——— PDF Pipeline Options ———
    pipeline_options = PdfPipelineOptions()
    pipeline_options.artifacts_path = artifacts_path
    pipeline_options.do_ocr = do_ocr
    pipeline_options.ocr_options = ocr_options
    # pipeline_options.do_table_structure = True
    # pipeline_options.table_structure_options.do_cell_matching = True
    # pipeline_options.accelerator_options = AcceleratorOptions(
    #     num_threads=4, device=AcceleratorDevice.AUTO
    # )

    # ——— DocumentConverter ———
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    # ——— 转换文档 ———
    result = converter.convert(
        source,
        max_num_pages=max_num_pages,
        max_file_size=max_file_size
    )

    return result


# ——— 测试流程 ——— #
if __name__ == "__main__":

    artifacts = r"C:\Users\zmn\.cache\docling\models"

    # 示例：PDF
    source_url = "https://arxiv.org/pdf/2408.09869"

    res = process_document(
        source=source_url,
        artifacts_path=artifacts,
        do_ocr=False,
        ocr_engine="easyocr"
    )

    # —— 根据文件类型选择导出 —— #

    file_type = 2
    # 1️⃣ Excel
    # if file_type in [".xls", ".xlsx", ".xlsm", ".xlsb"]:
    if file_type == 2:
        extract_output = res.document.export_to_html()

    # 2️⃣ 图片
    # elif file_type in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]:
    elif file_type ==3:
        try:
            extract_output = res.document.export_to_html()
        except Exception:
            extract_output = res.document.export_to_markdown()

    # 3️⃣ 其他（PDF / 文档）
    else:
        extract_output = res.document.export_to_markdown()

    print("--- extract result ---")
    print(extract_output)
