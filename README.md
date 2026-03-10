# PDF Bookmarks

使用视觉 LLM 自动为 PDF 电子书添加书签的工具。通过分析目录，自动生成书签并应用到 PDF 文件中。

## 功能特点

- 自动检测 PDF 中的目录页
- 使用视觉 LLM 提取书签信息
- 自动计算页码偏移量
- 支持多层级书签结构
- 使用文本 LLM 优化书签格式
- 基于 pdftk 的书签应用

## 平台安装指南

### Linux

#### 1. 安装 Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Fedora/RHEL
sudo dnf install python3 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

#### 2. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

或使用 pip：

```bash
pip install uv
```

#### 3. 安装 pdftk

```bash
# Ubuntu/Debian
sudo apt install pdftk

# Fedora/RHEL
sudo dnf install pdftk

# Arch Linux
sudo pacman -S pdftk
```

#### 4. 安装项目依赖

```bash
cd /path/to/pdf-bookmarks
uv sync
```

### macOS

#### 1. 安装 Python

使用 [Homebrew](https://brew.sh/)：

```bash
brew install python@3.12
```

或下载官方安装包：[python.org](https://www.python.org/downloads/)

#### 2. 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

或使用 Homebrew：

```bash
brew install uv
```

#### 3. 安装 pdftk

```bash
brew install pdftk-java
```

#### 4. 安装项目依赖

```bash
cd /path/to/pdf-bookmarks
uv sync
```

### Windows

#### 1. 安装 Python

1. 访问 [python.org](https://www.python.org/downloads/)
2. 下载 Python 3.10+ 安装包
3. 运行安装程序，**务必勾选 "Add Python to PATH"**

或使用 [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/)：

```powershell
winget install Python.Python.3.12
```

#### 2. 安装 uv

使用 PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

或下载独立的 uv 可执行文件：[github.com/astral-sh/uv](https://github.com/astral-sh/uv/releases)

#### 3. 安装 pdftk

1. 下载 [pdftk-server](https://www.pdflabs.com/tools/pdftk-server/)
2. 运行安装程序
3. 将 pdftk 添加到系统 PATH（安装程序通常会自动处理）

或使用 [Chocolatey](https://chocolatey.org/)：

```powershell
choco install pdftk
```

#### 4. 安装项目依赖

打开 Command Prompt 或 PowerShell：

```cmd
cd C:\path\to\pdf-bookmarks
uv sync
```

## 配置

在项目根目录创建 `model.env` 文件，配置以下环境变量：

```env
API_KEY=your_api_key_here
BASE_URL=https://api.example.com/v1
VISION_MODEL=gpt-4-vision-preview
TEXT_MODEL=gpt-4
```

## 使用方法

### 基本使用

```bash
# Linux / macOS
uv run pdf-bookmarks input.pdf output.pdf

# Windows
uv run pdf-bookmarks input.pdf output.pdf
```

### 通过 main.py 运行

```bash
# 所有平台
uv run python src/main.py input.pdf output.pdf
```

### 完整示例

```bash
# Linux / macOS
uv run python src/main.py ~/Documents/ebook.pdf ~/Documents/ebook_with_bookmarks.pdf

# Windows
uv run python src/main.py C:\Users\YourName\Documents\ebook.pdf C:\Users\YourName\Documents\ebook_with_bookmarks.pdf
```

## 工作原理

1. **扫描 TOC 页**：逐页扫描 PDF，使用视觉 LLM 识别目录页
2. **计算页码偏移**：找到第一个条目的页码，在实际 PDF 中定位其内容，计算偏移量
3. **提取书签信息**：从 TOC 页提取书签条目
4. **优化书签**：使用文本 LLM 检查和修复书签结构
5. **应用偏移量**：根据计算的偏移量调整页码
6. **生成 PDF**：使用 pdftk 将书签应用到 PDF

## 常见问题

### pdftk 命令未找到

确保 pdftk 已正确安装并添加到系统 PATH：

```bash
# Linux / macOS
which pdftk

# Windows
where pdftk
```

