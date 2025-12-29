"""
docling_processor_final.py

说明:
  - 最终优化版文档处理器。
  - 包含一个独立函数用于仅获取远程文件类型 (get_content_type_from_url)。
  - 主处理函数 (process_document) 会在下载前获取并记录文件类型。
  - 支持从 URL 或本地路径处理文件。
  - 支持限制文件大小与最大页数。
  - 可选择 OCR 引擎。
  - 导出 Markdown、JSON，并进行文档分块。
  - 运行前请确保已安装 docling 与 requests，并下载模型。
"""

import logging
import tempfile
import requests
from pathlib import Path
from typing import Optional, Dict, Any
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
logger = logging.getLogger("docling_processor_final")


# ----------------- 独立的类型获取函数 -----------------
def get_content_type_from_url(url: str, timeout: int = 10) -> Optional[str]:
    """
    通过HTTP请求获取远程URL的Content-Type，不下载文件内容。
    优先使用HEAD请求，失败后尝试GET请求（但不读取body）。
    """
    try:
        # 1. 尝试 HEAD 请求
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        content_type = response.headers.get("Content-Type")
        if content_type:
            return content_type.lower().strip()
        logger.debug(f"HEAD 请求未返回 Content-Type: {url}")
    except requests.RequestException as e:
        logger.debug(f"HEAD 请求失败 ({e}), 尝试 GET 请求: {url}")

    try:
        # 2. HEAD失败或无Content-Type，尝试 GET 请求（流式，不读body）
        response = requests.get(url, stream=True, allow_redirects=True, timeout=timeout)
        content_type = response.headers.get("Content-Type")
        response.close() # 立即关闭连接，不读取内容
        if content_type:
            return content_type.lower().strip()
        logger.debug(f"GET 请求也未返回 Content-Type: {url}")
    except requests.RequestException as e:
        logger.warning(f"获取 {url} 的 Content-Type 失败: {e}")

    return None



# ----------------- 内部转换器创建函数 -----------------
def _create_converter(artifacts_path: str, ocr_engine: str = "auto", enable_remote_services: bool = False):
    """根据配置创建 DocumentConverter 实例。"""
    logger.info(f"使用模型路径: {artifacts_path}")

    pdf_options_kwargs = {"artifacts_path": artifacts_path}
    ocr_engine = ocr_engine.lower()

    if ocr_engine == "easyocr":
        logger.info("启用 EasyOCR")
        pdf_options_kwargs.update({"do_ocr": True, "ocr_options": EasyOcrOptions()})
    elif ocr_engine == "tesseract":
        logger.info("启用 Tesseract OCR")
        pdf_options_kwargs.update({"do_ocr": True, "ocr_options": TesseractOcrOptions()})
    elif ocr_engine == "none":
        logger.info("禁用 OCR")
        pdf_options_kwargs["do_ocr"] = False
    else:
        logger.info(f"OCR 使用 auto 模式 (引擎: {ocr_engine})")

    pdf_options_kwargs["enable_remote_services"] = enable_remote_services

    pipeline_options = PdfPipelineOptions(**pdf_options_kwargs)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    return converter


# ----------------- 主处理函数 -----------------
def process_document(
    source: str,
    artifacts_path: str,
    *,
    ocr_engine: str = "auto",
    enable_remote_services: bool = False,
    max_num_pages: Optional[int] = 1000,
    max_file_size: Optional[int] = 50 * 1024 * 1024, # 50MB
) -> Dict[str, Any]:
    """
    处理单个文档（URL 或本地路径），返回包含 markdown/json/chunks/metadata 的字典。
    对于远程URL，在下载前会获取并记录其 Content-Type。
    """
    temp_path = None
    content_type = None # 初始化为 None

    try:
        if source.startswith(("http://", "https://")):
            # --- 获取远程文件类型 ---
            content_type = get_content_type_from_url(source)
            logger.info(f"检测到远程文件 Content-Type: {content_type}")

            # 检查远程文件大小
            try:
                head_resp = requests.head(source, timeout=10, allow_redirects=True)
                content_length = head_resp.headers.get("Content-Length")
                if content_length:
                    remote_size = int(content_length)
                    if max_file_size and remote_size > max_file_size:
                        raise ValueError(f"远程文件大小 ({remote_size} bytes) 超过限制 ({max_file_size} bytes)")
            except requests.RequestException as e:
                logger.warning(f"无法获取远程文件大小，跳过检查: {e}")

        # 创建转换器
        converter = _create_converter(
            artifacts_path=artifacts_path,
            ocr_engine=ocr_engine,
            enable_remote_services=enable_remote_services,
        )

        # 执行转换
        convert_kwargs = {}
        if max_num_pages:
            convert_kwargs["max_num_pages"] = max_num_pages
        logger.info(f"开始转换文档: {source}")
        result = converter.convert(str(source), **convert_kwargs)

        # 导出内容
        markdown_content = result.document.export_to_markdown()
        json_content = result.document.export_to_dict()

        # 分块
        chunks = list(HierarchicalChunker().chunk(result.document))

        logger.info(f"文档处理成功: {source}")
        return {
            "source": source,
            "local_path": str(source),
            "markdown": markdown_content,
            "json": json_content,
            "chunks": chunks,
            "meta": {"pages_processed": getattr(result, "pages_processed", None)},
            "detected_content_type": content_type, # 包含检测到的类型
        }

    finally:
        # 清理临时文件
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
                logger.info(f"已清理临时下载文件: {temp_path}")
            except OSError as e:
                logger.warning(f"删除临时文件失败 {temp_path}: {e}")


# ----------------- 示例 / 主程序 -----------------
if __name__ == "__main__":
    # --- 配置项 ---
    ARTIFACTS_PATH = r"C:\Users\zmn\.cache\docling\models"  # 请修改为实际路径
    OUTPUT_DIR = Path("../result_final")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # --- 示例 1: 仅获取远程文件类型 ---
    # URL_TO_CHECK = "https://arxiv.org/pdf/2408.09869.pdf"
    URL_TO_CHECK = "https://east196.blog.csdn.net/article/details/145716024"
    print("--- 仅获取远程文件类型示例 ---")
    file_type = get_content_type_from_url(URL_TO_CHECK)
    print(f"URL: {URL_TO_CHECK}")
    print(f"Content-Type: {file_type}\n")

    # --- 示例 2: 处理文档（包含类型获取） ---
    PDF_URL = "https://arxiv.org/pdf/2408.09869.pdf"
    try:
        logger.info("--- 处理远程 PDF 示例 ---")
        res = process_document(
            PDF_URL,
            ARTIFACTS_PATH,
            ocr_engine="auto",
            max_num_pages=5, # 限制页数加快测试
        )
        (OUTPUT_DIR / "final_pdf.md").write_text(res["markdown"], encoding="utf-8")
        logger.info(f"PDF 处理完成，Markdown 长度: {len(res['markdown'])}, 检测到的类型: {res['detected_content_type']}")
        if res["chunks"]:
             logger.info(f"首个分块预览: {str(res['chunks'][0])[:200]}...")
    except Exception as e:
        logger.error(f"处理 PDF URL 失败: {e}")

    # --- 示例 3: 处理远程 HTML ---
    HTML_URL = "https://east196.blog.csdn.net/article/details/145716024"
    try:
        logger.info("--- 处理远程 HTML 示例 ---")
        res2 = process_document(HTML_URL, ARTIFACTS_PATH, ocr_engine="none")
        (OUTPUT_DIR / "final_html.md").write_text(res2["markdown"], encoding="utf-8")
        logger.info(f"HTML 处理完成，Markdown 长度: {len(res2['markdown'])}, 检测到的类型: {res2['detected_content_type']}")
    except Exception as e:
        logger.error(f"处理 HTML URL 失败: {e}")
