from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker import HierarchicalChunker

artifacts_path = "C:\\Users\zmn\.cache\docling\models"
# source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
source = "https://east196.blog.csdn.net/article/details/145716024?fromshare=blogdetail&sharetype=blogdetail&sharerId=145716024&sharerefer=PC&sharesource=qq_51744378&sharefrom=from_link"  # document per local path or URL

pipeline_options = PdfPipelineOptions(
    artifacts_path=artifacts_path,
    # do_ocr=True,  # 使用OCR，针对扫描版 PDF
    # ocr_options=EasyOcrOptions(),
    # enable_remote_services=True
)
doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# result = doc_converter.convert(source)
result = doc_converter.convert(source, max_num_pages=100, max_file_size=20971520)   # 限制每个文档允许处理的文件大小和页数

markdown_content = result.document.export_to_markdown()
print(markdown_content)

json_content = result.document.export_to_dict()
print(json_content)

# 文档分块
chunks = list(HierarchicalChunker().chunk(result.document))
print(chunks[0])

print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"