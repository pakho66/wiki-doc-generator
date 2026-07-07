# wiki-doc-generator

将 Markdown 文档一键转换为**飞书/Lark Wiki 风格**的专业在线知识库页面。

## 效果预览

生成的页面包含：
- 🎨 深色渐变 Banner 标题区
- 📑 左侧固定导航栏（自动提取章节标题）
- 📝 完整正文渲染（表格、引用、代码块、高亮标记）
- 📱 移动端响应式适配
- ⬆️ 回到顶部按钮

## 安装

```bash
pip install -e git+https://github.com/pakho66/wiki-doc-generator.git
```

或者克隆后本地安装：

```bash
git clone https://github.com/pakho66/wiki-doc-generator.git
cd wiki-doc-generator
pip install -e .
```

## 使用

```bash
# 基本用法：生成到 docs/index.html
wiki-gen README.md

# 指定输出目录
wiki-gen 文档.md -o ./public/

# 自定义页面标题
wiki-gen 文档.md --title "我的知识库"

# 也可以直接运行 Python 脚本
python wiki_gen.py 文档.md -o output/
```

## 特性

- **零依赖**：仅使用 Python 标准库，无需安装任何第三方包
- **单文件输出**：生成的 HTML 完全自包含（CSS/JS 全部内联）
- **飞书 Wiki 风格**：布局、配色、交互完整模仿飞书知识库
- **自动导航**：从 Markdown H2/H3 标题自动生成侧边栏目录
- **完整渲染**：支持表格、引用块、代码块、列表、高亮标记等
- **点击跳转**：导航点击平滑滚动，当前章节自动高亮

## GitHub Pages 自动部署

在仓库中创建 `.github/workflows/deploy.yml`：

```yaml
name: Build and Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python wiki_gen.py README.md -o public/
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```

之后在 GitHub 仓库 Settings → Pages 中启用 GitHub Pages 即可。

## License

MIT
