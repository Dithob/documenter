from docling.document_converter import DocumentConverter
source = "https://oss-pub.xiujiadian.com/41/365/1071/20251225/7cf89a1b-e407-4975-a6f2-ba3a2d2efd3c.png"  # document per local path or URL
converter = DocumentConverter()
doc = converter.convert(source).document
print(doc.export_to_markdown())
# output: ## Docling Technical Report [...]"