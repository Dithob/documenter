from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import PdfFormatOption, DocumentConverter, ImageFormatOption, PowerpointFormatOption, \
    WordFormatOption, ExcelFormatOption, HTMLFormatOption
from docling_core.transforms.chunker import HierarchicalChunker



artifacts_path = "/a/domains/docling/docling_models"
# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
source = "https://east196.blog.csdn.net/article/details/145716024?fromshare=blogdetail&sharetype=blogdetail&sharerId=145716024&sharerefer=PC&sharesource=qq_51744378&sharefrom=from_link"  # document per local path or URL

image_url = "https://oss-pub.xiujiadian.com/41/365/1071/20251225/7cf89a1b-e407-4975-a6f2-ba3a2d2efd3c.png"

# 指定模型路径
easyocr_model_storage_directory = '/a/domains/docling/docling_models/easyocr'  # 使用绝对路径
# 指定OCR模型
easyocr_options = EasyOcrOptions()
# 可以不设置，默认语言：["fr", "de", "es", "en"]
easyocr_options.lang = ['ch_sim', 'en']  # 中英文
easyocr_options.model_storage_directory = easyocr_model_storage_directory

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
# pipeline_options.do_table_structure = True
pipeline_options.ocr_options = easyocr_options
# pipeline_options.enable_remote_services=True


doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
        InputFormat.PPTX: PowerpointFormatOption(pipeline_options=pipeline_options),
        InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options),
        InputFormat.XLSX: ExcelFormatOption(pipeline_options=pipeline_options),
        InputFormat.HTML: HTMLFormatOption(pipeline_options=pipeline_options)
    }
)

# result = doc_converter.convert(source)
result = doc_converter.convert(image_url, max_num_pages=100, max_file_size=20971520)   # 限制每个文档允许处理的文件大小和页数

markdown_content = result.document.export_to_markdown()
print("--- markdown result ---")
print(markdown_content)

json_content = result.document.export_to_dict()
print("--- json result ---")
print(json_content)

html_content = result.document.export_to_html()
print("--- html result ---")
print(html_content)

# 文档分块
chunks = list(HierarchicalChunker().chunk(result.document))
print("--- chunks result ---")
print(chunks[0])
