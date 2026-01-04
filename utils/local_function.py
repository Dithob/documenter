from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, RapidOcrOptions, AcceleratorOptions, AcceleratorDevice
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
    # rapidocr_options = RapidOcrOptions()
    rapidocr_options = RapidOcrOptions(force_full_page_ocr=True)    # 强制整页OCR
    rapidocr_options.lang = ocr_lang
    if ocr_model_storage_directory:
       rapidocr_options.model_storage_directory = ocr_model_storage_directory

    # 配置PDF处理管道
    pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
    pipeline_options.do_ocr = enable_ocr
    pipeline_options.do_table_structure = enable_table_structure
    # pipeline_options.ocr_options = easyocr_options
    pipeline_options.ocr_options = rapidocr_options

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4, device=AcceleratorDevice.AUTO
    )

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
    source = "https://oss-pub.xiujiadian.com/41/365/1071/20251210/5fc3e2b2-5f76-4f82-ae3d-aa1bfae1dae7.png"
    file_converter = create_docling_converter(artifacts_path=artifacts_dir, ocr_model_storage_directory=ocr_directory)
    extract_result = file_converter.convert(source)


    # output_dir = Path("/a/domains/docling/docling_master/result_files/save_files")
    output_dir = Path("save_files")
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = extract_result.input.file.stem


    # md_filename = output_dir / f"{doc_filename}-with-images.md"
    # extract_result.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)
    html_filename = output_dir / f"{doc_filename}-with-image-refs.html"
    extract_result.document.save_as_html(html_filename, image_mode=ImageRefMode.REFERENCED)

    markdown_output = extract_result.document.export_to_markdown()
    print("--- markdown result ---")
    print(markdown_output)
    # print("--- result ---")
    # print(extract_result)