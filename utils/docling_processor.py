"""
docling_processor_cn.py

说明:
  - 该脚本封装了对各种文档（PDF / HTML / 图片 / Office）的识别流程：
    - 支持从 URL 下载或处理本地文件
    - 支持限制文件大小与最大页数
    - 可选择 OCR 引擎 (easyocr / tesseract / none / auto)
    - 导出 Markdown、JSON，并做文档分块（HierarchicalChunker）
  - 运行前请确保已安装 docling 与 requests，并把 docling 模型放到 artifacts_path
    (可用 `docling-tools models download --output-dir ...` 预下载模型)

使用:
  python docling_processor_cn.py
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
import requests

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TesseractOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker import HierarchicalChunker

# ---------------- 日志配置 ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("docling_processor_cn")


# ----------------- 工具函数 -----------------
def normalize_artifacts_path(p: str) -> str:
    """规范化 artifacts_path（展开 ~ 并返回绝对路径），兼容 Windows 路径。"""
    return str(Path(p).expanduser().resolve())


def is_url(source: str) -> bool:
    """判断字符串是否为 http/https URL。"""
    try:
        parsed = urlparse(source)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def head_remote_file(url: str, timeout: int = 10) -> Tuple[Optional[int], Optional[str]]:
    """
    尝试通过 HEAD 获取远程文件的 Content-Length 与 Content-Type。
    若服务器不支持 HEAD，则回退到 GET（stream）。
    返回 (size_bytes_or_None, content_type_or_None)
    """
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        if r.status_code >= 400:
            r = requests.get(url, stream=True, timeout=timeout)
        size = r.headers.get("Content-Length")
        ctype = r.headers.get("Content-Type")
        return (int(size) if size and size.isdigit() else None, ctype)
    except Exception as e:
        logger.debug("head_remote_file 失败: %s", e)
        return None, None


def download_to_temp(url: str, max_size: Optional[int] = None, timeout: int = 30) -> Path:
    """
    将远程文件流式下载到临时文件夹，若超过 max_size 则抛出异常并清理。
    返回临时文件路径（调用方负责文件会被我们在 finally 中清理）。
    """
    logger.info("开始下载：%s", url)
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()

    tmp_dir = Path(tempfile.mkdtemp())
    tmp_file = tmp_dir / Path(urlparse(url).path).name
    total = 0
    with open(tmp_file, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if not chunk:
                continue
            f.write(chunk)
            total += len(chunk)
            if max_size and total > max_size:
                # 清理并抛错
                f.close()
                tmp_file.unlink(missing_ok=True)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise ValueError(f"远程文件超过允许大小：{total} bytes > {max_size} bytes")
    logger.info("下载完成 -> %s (%d bytes)", tmp_file, total)
    return tmp_file


def detect_input_format_from_path(path: Path, content_type: Optional[str] = None) -> InputFormat:
    """
    简单根据文件扩展名或 content-type 映射到 docling 的 InputFormat。
    可按需扩展更多类型映射。
    """
    suffix = (path.suffix or "").lower()
    if content_type:
        c = content_type.lower()
        if "pdf" in c:
            return InputFormat.PDF
        if "html" in c or "text" in c:
            return InputFormat.HTML
        if "image" in c:
            return InputFormat.IMAGE

    if suffix in [".pdf"]:
        return InputFormat.PDF
    if suffix in [".html", ".htm"]:
        return InputFormat.HTML
    if suffix in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif", ".webp"]:
        return InputFormat.IMAGE
    # 默认为 PDF（docling 通常能根据内容调整）；避免使用未知常量导致属性错误
    return InputFormat.PDF


# ------------- 构造 DocumentConverter -------------
def build_document_converter(
    artifacts_path: str,
    ocr_engine: str = "auto",  # 支持 "easyocr", "tesseract", "none", "auto"
    enable_remote_services: bool = False,
) -> DocumentConverter:
    """
    根据本地模型路径与 OCR 配置构造 DocumentConverter。
    artifacts_path: 本地模型目录（已下载的 docling 模型）
    ocr_engine: OCR 引擎选择
    enable_remote_services: 若本地模型不足是否允许远程服务回退
    """
    artifacts_path = normalize_artifacts_path(artifacts_path)
    logger.info("使用的 artifacts 路径: %s", artifacts_path)

    pdf_opts_kwargs: Dict[str, Any] = {"artifacts_path": artifacts_path}

    ocr_engine = (ocr_engine or "auto").lower()
    if ocr_engine == "easyocr":
        logger.info("配置 EasyOCR")
        pdf_opts_kwargs["do_ocr"] = True
        pdf_opts_kwargs["ocr_options"] = EasyOcrOptions()
    elif ocr_engine == "tesseract":
        logger.info("配置 Tesseract OCR")
        pdf_opts_kwargs["do_ocr"] = True
        pdf_opts_kwargs["ocr_options"] = TesseractOcrOptions()
    elif ocr_engine == "none":
        logger.info("禁用 OCR")
        pdf_opts_kwargs["do_ocr"] = False
    else:
        logger.info("OCR 使用 auto 模式（不强制开启），enable_remote_services=%s", enable_remote_services)
        # 不设置 do_ocr，交给 docling 根据内容判断

    if enable_remote_services:
        pdf_opts_kwargs["enable_remote_services"] = True

    pipeline_options = PdfPipelineOptions(**pdf_opts_kwargs)
    format_options = {InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}

    converter = DocumentConverter(format_options=format_options)
    logger.debug("已创建 DocumentConverter")
    return converter


# ----------------- 主处理函数 -----------------
def process_document(
    source: str,
    artifacts_path: str,
    *,
    ocr_engine: str = "auto",
    enable_remote_services: bool = False,
    max_num_pages: Optional[int] = 1000,
    max_file_size: Optional[int] = 50 * 1024 * 1024,  # 默认 50MB
) -> Dict[str, Any]:
    """
    处理单个文档（URL 或本地路径），返回包含 markdown/json/chunks/metadata 的字典。
    函数会在完成后清理临时下载文件（若有）。
    """
    tmp_file: Optional[Path] = None
    try:
        # 1) 判断 URL 或本地文件，并可能下载到临时文件
        if is_url(source):
            remote_size, content_type = head_remote_file(source)
            if remote_size and max_file_size and remote_size > max_file_size:
                raise ValueError(f"远程文件太大：{remote_size} bytes > {max_file_size} bytes")
            tmp_file = download_to_temp(source, max_size=max_file_size)
            input_path = tmp_file
            detected_format = detect_input_format_from_path(input_path, content_type)
        else:
            input_path = Path(source)
            if not input_path.exists():
                raise FileNotFoundError(f"本地文件不存在：{input_path}")
            detected_format = detect_input_format_from_path(input_path)

        logger.info("检测到输入格式: %s", detected_format)

        # 2) 创建或复用 converter（若批量处理建议外部创建一次并循环使用）
        converter = build_document_converter(
            artifacts_path=artifacts_path,
            ocr_engine=ocr_engine,
            enable_remote_services=enable_remote_services,
        )

        # 3) 执行转换
        convert_kwargs = {}
        if max_num_pages:
            convert_kwargs["max_num_pages"] = max_num_pages
        logger.info("开始转换，参数: %s", convert_kwargs)
        result = converter.convert(str(input_path), **convert_kwargs)

        # 4) 导出内容
        markdown_content = result.document.export_to_markdown()
        json_content = result.document.export_to_dict()

        # 5) 分块
        chunks = list(HierarchicalChunker().chunk(result.document))

        return {
            "source": source,
            "local_path": str(input_path),
            "markdown": markdown_content,
            "json": json_content,
            "chunks": chunks,
            "meta": {"pages_processed": getattr(result, "pages_processed", None)},
        }

    finally:
        # 清理下载的临时文件夹
        if tmp_file:
            try:
                tmp_parent = tmp_file.parent
                tmp_file.unlink(missing_ok=True)
                shutil.rmtree(tmp_parent, ignore_errors=True)
                logger.info("已清理临时文件。")
            except Exception as e:
                logger.debug("清理临时文件出错: %s", e)


# ----------------- 示例 / 主程序 -----------------
if __name__ == "__main__":
    # --- 配置项（请根据环境修改） ---
    artifacts_path = r"C:\Users\zmn\.cache\docling\models"  # Windows 示例（使用原始字符串避免转义）
    # artifacts_path = "/home/user/.cache/docling/models"   # Linux 示例
    out_dir = Path("../result_files")
    # 示例 1: 处理 arXiv PDF（远程）
    pdf_url = "https://arxiv.org/pdf/2408.09869.pdf"
    # try:
    #     out = process_document(
    #         pdf_url,
    #         artifacts_path,
    #         ocr_engine="auto",
    #         enable_remote_services=False,
    #         max_num_pages=100,
    #         max_file_size=20 * 1024 * 1024,  # 20 MB
    #     )
    #
    #     out_dir.mkdir(exist_ok=True)
    #     Path(out_dir / "doc.md").write_text(out["markdown"], encoding="utf-8")
    #     Path(out_dir / "doc.json").write_text(out["json"], encoding="utf-8")
    #     logger.info("保存输出到 %s", out_dir)
    #     if out["chunks"]:
    #         logger.info("首个分块预览: %s", out["chunks"][0])
    # except Exception as e:
    #     logger.exception("处理 PDF URL 失败: %s", e)

    # 示例 2: 处理 HTML 博客（如果 docling 支持 HTML 输入）
    blog_url = "https://east196.blog.csdn.net/article/details/145716024"
    try:
        out2 = process_document(blog_url, artifacts_path, ocr_engine="none", enable_remote_services=True)
        Path(out_dir / "doc2.md").write_text(out2["markdown"], encoding="utf-8")
        logger.info("处理博客完成；Markdown 长度: %d", len(out2["markdown"]))
    except Exception as e:
        logger.exception("处理博客 URL 失败: %s", e)

    # 示例 3: 处理本地文件（取消注释并修改路径以运行）
    # local_path = r"C:\path\to\local\document.pdf"
    # try:
    #     out3 = process_document(local_path, artifacts_path, ocr_engine="easyocr")
    #     logger.info("本地处理完成。Markdown 长度: %d", len(out3['markdown']))
    # except Exception as e:
    #     logger.exception("处理本地文件失败: %s", e)
