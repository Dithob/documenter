from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
from docling.datamodel.pipeline_options import PictureDescriptionVlmOptions, granite_picture_description
from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import PictureDescriptionData
from IPython import display

DOC_SOURCE = "https://oss-pub.xiujiadian.com/41/365/1071/20251210/5fc3e2b2-5f76-4f82-ae3d-aa1bfae1dae7.png"
pipeline_options = PdfPipelineOptions(artifacts_path="/a/domains/docling/docling_models")

pipeline_options.do_picture_description = True
temp_picture_description = PictureDescriptionVlmOptions(
    repo_id="Qwen/Qwen3-VL-2B-Instruct",
    prompt="详细描述一下这张图片",
    generation_config = dict(max_new_tokens=500, do_sample=False)
)

# temp_picture_description = granite_picture_description
# # 设置本地模型id
# temp_picture_description.repo_id = "Qwen/Qwen3-VL-2B-Instruct"
# temp_picture_description.repo_id = "ibm-granite/granite-vision-3.2-2b"
# # 设置最大生成长度
# temp_picture_description.generation_config = dict(max_new_tokens=500, do_sample=False)

pipeline_options.picture_description_options = (
    temp_picture_description  # <-- the model choice
)
# 模型提示词
# pipeline_options.picture_description_options.prompt = (
#     "详细描述一下这张图片"
#     # "Describe the image in detail"
#     # "Describe the image in three sentences. Be consise and accurate."
# )

pipeline_options.images_scale = 2.0
pipeline_options.generate_picture_images = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options,
        ),
        InputFormat.IMAGE: ImageFormatOption(
            pipeline_options=pipeline_options
        )
    }
)
extract_result = converter.convert(DOC_SOURCE)
markdown_output = extract_result.document.export_to_markdown()
print("--- markdown result ---")
print(markdown_output)

annotation = extract_result.document.pictures[0].annotations
print("--- annotation result ---")
print(annotation)

output_dir = Path("save_files")
output_dir.mkdir(parents=True, exist_ok=True)
doc_filename = extract_result.input.file.stem
html_filename = output_dir / f"{doc_filename}-with-images.md"
extract_result.document.save_as_markdown(html_filename, image_mode=ImageRefMode.REFERENCED)