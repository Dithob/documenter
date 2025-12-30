from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, RapidOcrOptions
from docling.document_converter import PdfFormatOption, DocumentConverter, ImageFormatOption, PowerpointFormatOption, \
    WordFormatOption, ExcelFormatOption, HTMLFormatOption, StandardPdfPipeline

from docling_core.types.doc.base import ImageRefMode


def create_docling_converter(
        artifacts_path="/a/domains/docling/docling_models",
        ocr_lang=None,
        ocr_model_storage_directory="/a/domains/docling/docling_models/easyocr",
        enable_ocr=True,
        enable_table_structure=True
):
    """
    创建一个配置好的Docling DocumentConverter实例。

    Args:
        artifacts_path (str): 模型文件的存储路径。
        ocr_lang (list): OCR语言列表，默认为['ch_sim', 'en']。
        ocr_model_storage_directory (str, optional): EasyOCR模型存储目录。
        enable_ocr (bool): 是否启用OCR。
        enable_table_structure (bool): 是否启用表格结构识别。

    Returns:
        DocumentConverter: 配置好的转换器实例。
    """
    if ocr_lang is None:
        ocr_lang = ['ch_sim', 'en']

    # # 配置EasyOcrOptions选项
    # easyocr_options = EasyOcrOptions()
    # easyocr_options.lang = ocr_lang
    # if ocr_model_storage_directory:
    #     easyocr_options.model_storage_directory = ocr_model_storage_directory

    # 配置RapidOcrOptions选项
    rapidocr_options = RapidOcrOptions()
    #    rapidocr_options.lang = ocr_lang
    #    if ocr_model_storage_directory:
    #        rapidocr_options.model_storage_directory = ocr_model_storage_directory

    # 配置PDF处理管道
    pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
    pipeline_options.do_ocr = enable_ocr
    pipeline_options.do_table_structure = enable_table_structure
    # pipeline_options.ocr_options = easyocr_options
    pipeline_options.ocr_options = rapidocr_options

    # 提取图片选项
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True
    # pipeline_options.generate_table_images = True     # 已弃用
    pipeline_options.images_scale = 1.5  # 可选，提高分辨率
    # 创建转换器
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
            InputFormat.PPTX: PowerpointFormatOption(pipeline_options=pipeline_options),
            InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options),
            InputFormat.XLSX: ExcelFormatOption(pipeline_options=pipeline_options),
            InputFormat.HTML: HTMLFormatOption(pipeline_options=pipeline_options)
        }
    )
    return converter


def process_document(source_file, converter=None, artifacts_path="/a/domains/docling/docling_models"):
    if converter is None:
        converter = create_docling_converter(artifacts_path=artifacts_path)

    # 使用转换器处理文档 [[5]]
    result = converter.convert(source)
    # 输出为markdown格式
    return result.document.export_to_markdown()


if __name__ == '__main__':
    artifacts_dir = "/a/domains/docling/docling_models"
    ocr_directory = '/a/domains/docling/docling_models/RapidOcr'
    source = "https://oss-pub.xiujiadian.com/41/365/1071/20251225/66079fca-56e1-4744-a698-36aa5aa54904.png"
    file_converter = create_docling_converter(artifacts_path=artifacts_dir, ocr_model_storage_directory=ocr_directory)
    extract_result = file_converter.convert(source)
    markdown_output = extract_result.document.export_to_markdown()

    output_dir = Path("/a/domains/docling/docling_master/result_files/save_files")
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = extract_result.input.file.stem

    # Export Markdown format:
    # with (output_dir / f"{doc_filename}.md").open("w", encoding="utf-8") as fp:
    #     fp.write(extract_result.document.export_to_markdown())

    # save as markdown with image
    extract_result.document.save_as_markdown('./out_md', image_mode=ImageRefMode.REFERENCED)

    print("--- markdown result ---")
    print(markdown_output)
#    print("--- result ---")
#    print(extract_result)