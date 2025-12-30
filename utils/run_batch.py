from datetime import datetime

import pandas as pd
from pathlib import Path
from local_function import create_docling_converter

def batch_process_excel(input_excel_path, output_excel_path, artifacts_path, ocr_model_path):
    """
    批量处理Excel文件中的URL，调用文档处理方法并将结果保存到输出列

    Args:
        input_excel_path: 输入Excel文件路径
        output_excel_path: 输出Excel文件路径
        artifacts_path: 模型缓存路径
        ocr_model_path: OCR模型路径
    """

    # 读取Excel文件
    df = pd.read_excel(input_excel_path)
    converter = create_docling_converter(artifacts_path=artifacts_path, ocr_model_storage_directory=ocr_model_path)
    # 确保输出列存在
    if '输出' not in df.columns:
        df['输出'] = ''

    # 遍历每一行进行处理
    for index, row in df.iterrows():
        try:
            source_url = str(row['文件URL']).strip() if pd.notna(row['文件URL']) else ''
            file_type = row['文件类型'] if pd.notna(row['文件类型']) else 0

            if not source_url:
                df.at[index, '输出'] = '错误：文件URL为空'
                continue

            print(f"正在处理第{index + 1}行: {source_url}")

            # 调用文档处理方法
            res = converter.convert(source_url)
            # 根据文件类型选择导出格式
            if file_type == 2:  # Excel
                extract_output = res.document.export_to_html()
            elif file_type == 3:  # 图片
                try:
                    extract_output = res.document.export_to_markdown()
                except Exception:
                    extract_output = res.document.export_to_html()
            else:  # 其他（PDF/文档）
                extract_output = res.document.export_to_markdown()

            # 将处理结果保存到输出列
            df.at[index, '输出'] = extract_output

        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            df.at[index, '输出'] = error_msg
            print(f"第{index + 1}行处理失败: {error_msg}")

    # 保存结果到Excel文件
    df.to_excel(output_excel_path, index=False)
    print(f"批量处理完成，结果已保存到: {output_excel_path}")


# ——— 批量运行脚本 ——— #
if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 配置参数
    artifacts = "/a/domains/docling/docling_models"  # 模型缓存路径
    ocr_path = "/a/domains/docling/docling_models/RapidOcr"
    input_file = "/a/domains/docling/docling_master/文档解析测试集_20251225_v0.1.xlsx"  # 输入Excel文件路径
    output_file = f"/a/domains/docling/docling_master/result_files/output_results_{timestamp}.xlsx"  # 输出Excel文件路径

    # 执行批量处理
    batch_process_excel(
        input_excel_path=input_file,
        output_excel_path=output_file,
        artifacts_path=artifacts,
        ocr_model_path=ocr_path
    )