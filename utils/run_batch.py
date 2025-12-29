import pandas as pd
from pathlib import Path
from  docling_func import process_document

def batch_process_excel(input_excel_path, output_excel_path, artifacts_path):
    """
    批量处理Excel文件中的URL，调用文档处理方法并将结果保存到输出列

    Args:
        input_excel_path: 输入Excel文件路径
        output_excel_path: 输出Excel文件路径
        artifacts_path: 模型缓存路径
    """

    # 读取Excel文件
    df = pd.read_excel(input_excel_path)

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
            res = process_document(
                source=source_url,
                artifacts_path=artifacts_path,
                do_ocr=True,
                ocr_engine="easyocr"
            )

            # 根据文件类型选择导出格式
            if file_type == 2:  # Excel
                extract_output = res.document.export_to_html()
            elif file_type == 3:  # 图片
                try:
                    extract_output = res.document.export_to_html()
                except Exception:
                    extract_output = res.document.export_to_markdown()
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
    # 配置参数
    artifacts = r"C:\Users\zmn\.cache\docling\models"  # 模型缓存路径
    input_file = "input_documents.xlsx"  # 输入Excel文件路径
    output_file = "output_results.xlsx"  # 输出Excel文件路径

    # 执行批量处理
    batch_process_excel(
        input_excel_path=input_file,
        output_excel_path=output_file,
        artifacts_path=artifacts
    )