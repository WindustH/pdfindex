# pdfindex

> 使用视觉模型自动为 PDF 电子书添加书签的工具

pdfindex 是一个智能的 PDF 书签生成工具，它能够自动识别电子书中的目录页面，使用视觉大语言模型提取书签信息，并自动为 PDF 添加导航书签。

## 功能特点

- **自动目录检测**：智能识别 PDF 中的目录/索引页面
- **视觉模型提取**：使用先进的视觉大模型准确提取书签结构
- **页码偏移校准**：自动计算页码偏移量，确保书签跳转准确
- **层级结构保留**：保持原书的章节层级关系
- **罗马数字过滤**：自动排除使用罗马数字编号的前言、目录等页面

## 安装

### 依赖要求

- Python >= 3.13
- [pdftk](https://www.pdflabs.com/tools/pdftk-server/) - 必须安装并可在 PATH 中访问

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/yourusername/pdfindex.git
cd pdfindex

# 使用 uv 安装依赖
uv sync
```

### pdftk 安装

- **Arch Linux**: `sudo pacman -S pdftk`
- **Ubuntu/Debian**: `sudo apt install pdftk`
- **macOS**: `brew install pdftk`

## 配置

设置以下环境变量：

```bash
export PDFINDEX_API_KEY=your_api_key_here
export PDFINDEX_BASE_URL=https://api.example.com/v1
export PDFINDEX_VISION_MODEL=gpt-4o
```

或者在使用前临时设置：

```bash
PDFINDEX_API_KEY=your_key PDFINDEX_BASE_URL=https://api.example.com/v1 PDFINDEX_VISION_MODEL=gpt-4o python main.py input.pdf output.pdf
```

## 使用方法

```bash
python main.py input.pdf output.pdf
```

### 参数说明

- `input_path` - 输入 PDF 文件路径
- `output_path` - 输出 PDF 文件路径（将包含书签）

### 示例

```bash
# 为电子书添加书签
python main.py ~/Downloads/ebook.pdf ~/Downloads/ebook_bookmarked.pdf
```

## 工作原理

1. **扫描目录页**：逐页扫描 PDF，识别目录页面
2. **提取书签信息**：使用视觉模型从目录页提取章节标题和页码
3. **计算页码偏移**：通过定位第一个阿拉伯数字编号的章节，计算实际页码与目录页码的偏移量
4. **生成书签文件**：生成 pdftk 格式的书签文件
5. **应用书签**：使用 pdftk 将书签嵌入 PDF

## 项目结构

```
pdfindex/
├── main.py           # 主程序入口
├── pyproject.toml    # 项目配置
└── README.md         # 项目文档
```

## 开发

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行程序
python main.py input.pdf output.pdf
```

## 依赖项

- `fitz` (PyMuPDF) - PDF 页面渲染
- `pypdf` - PDF 文件读取
- `pillow` - 图像处理
- `openai` - 视觉模型 API 调用

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
