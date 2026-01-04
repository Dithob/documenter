
```cmd
conda create -n docling_env python=3.10
conda activate docling_env
docling-tools models download


python anylaze_output.py --input ./static/文档解析_输出结果对比_20251230_151152.xlsx --output report.xlsx
```