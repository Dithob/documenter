import json
import time
from pathlib import Path
from docling_core.types.doc import DocItemLabel, ImageRefMode
from docling_core.types.doc.document import DEFAULT_EXPORT_LABELS
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    VlmPipelineOptions,
    smoldocling_vlm_mlx_conversion_options,
    granite_vision_vlm_conversion_options
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline, InlineVlmOptions
sources = [
    "https://oss-pub.xiujiadian.com/41/365/1071/20251224/2ffc8ab1-9601-4a95-91f4-28f32aac79f0.png",
    "https://oss-pub.xiujiadian.com/41/365/1071/20251216/dc6130b9-8be8-4807-94d2-dccb8a02ab4a.pptx",
]
from transformers import AutoModel, AutoTokenizer

## Use experimental VlmPipeline
pipeline_options = VlmPipelineOptions()
# If force_backend_text = True, text from backend will be used instead of generated text
pipeline_options.force_backend_text = False

## 选择一个 VLM 模型
# pipeline_options.vlm_options = smoldocling_vlm_mlx_conversion_options
model = AutoModel.from_pretrained("/a/domains/docling/docling_models/ibm-granite--granite-vision-3.2-2b", local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained("/a/domains/docling/docling_models/ibm-granite--granite-vision-3.2-2b", local_files_only=True)

vlm_opts = InlineVlmOptions(
    model=model,
    tokenizer=tokenizer,
    prompt="Convert this page to markdown. Do not miss any text and only output the bare markdown!",
)

local_granite_options = granite_vision_vlm_conversion_options
local_granite_options.model = model
# local_granite_option.prompt = ""
pipeline_options.vlm_options = vlm_opts    # 备用模型

## Set up pipeline for PDF or image inputs
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=VlmPipeline,
            pipeline_options=pipeline_options,
        ),
        InputFormat.IMAGE: PdfFormatOption(
            pipeline_cls=VlmPipeline,
            pipeline_options=pipeline_options,
        ),
    }
)
out_path = Path("scratch")
out_path.mkdir(parents=True, exist_ok=True)
for source in sources:
    start_time = time.time()
    print("================================================")
    print(f"Processing... {source}")
    print("================================================")
    print("")

    res = converter.convert(source)

    print("")
    print(res.document.export_to_markdown())

    for page in res.pages:
        print("")
        print("Predicted page in DOCTAGS:")
        print(page.predictions.vlm_response.text)

    res.document.save_as_html(
        filename=Path(f"{out_path}/{res.input.file.stem}.html"),
        image_mode=ImageRefMode.REFERENCED,
        labels=[*DEFAULT_EXPORT_LABELS, DocItemLabel.FOOTNOTE],
    )

    with (out_path / f"{res.input.file.stem}.json").open("w") as fp:
        fp.write(json.dumps(res.document.export_to_dict()))

    res.document.save_as_json(
        out_path / f"{res.input.file.stem}.json",
        image_mode=ImageRefMode.PLACEHOLDER,
    )

    res.document.save_as_markdown(
        out_path / f"{res.input.file.stem}.md",
        image_mode=ImageRefMode.PLACEHOLDER,
    )

    pg_num = res.document.num_pages()
    print("")
    inference_time = time.time() - start_time
    print(
        f"Total document prediction time: {inference_time:.2f} seconds, pages: {pg_num}"
    )
print("================================================")
print("done!")
print("================================================")