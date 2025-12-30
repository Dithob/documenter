import pathlib

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import PdfFormatOption, DocumentConverter, ImageFormatOption, PowerpointFormatOption, \
    WordFormatOption, ExcelFormatOption, HTMLFormatOption

# 指定模型路径
easyocr_model_storage_directory = '/a/domains/docling/docling_models/easyocr'  # 使用绝对路径
# 指定OCR模型
easyocr_options = EasyOcrOptions()
# 可以不设置，默认语言：["fr", "de", "es", "en"]
easyocr_options.lang = ['ch_sim', 'en']  # 中英文
easyocr_options.model_storage_directory = easyocr_model_storage_directory

artifacts_path = "/a/domains/docling/docling_models/docling-models"  # 使用绝对路径
pipeline_options = PdfPipelineOptions(artifacts_path=artifacts_path)
# 设置支持OCR
pipeline_options.do_ocr = True
# 设置支持表结构
pipeline_options.do_table_structure = True

# 指定OCR模型
pipeline_options.ocr_options = easyocr_options

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

source = "https://oss-pub.xiujiadian.com/41/365/1071/20251225/7cf89a1b-e407-4975-a6f2-ba3a2d2efd3c.png"
result = converter.convert(source)
print(result.document.export_to_markdown())  # 输出为markdown格式
# print(result.document.export_to_dict())    # 输出为json格式
# 除markdown、json还支持其他格式输出