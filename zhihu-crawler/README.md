# 知乎数据爬虫工具

基于 Playwright 的知乎数据爬取工具，支持关键词搜索和详情页爬取，图形界面操作，简单易用。

## 功能

- **关键词搜索**：输入关键词，搜索知乎相关回答、文章、视频
- **详情页爬取**：输入知乎链接，爬取指定内容详情及评论
- **图形界面**：可视化操作，无需命令行
- **数据导出**：自动保存为 CSV 文件，可用 Excel 打开

## 环境要求

- Windows 10/11
- Python 3.9+
- 网络连接

## 安装

```bash
# 1. 进入项目目录（一定要在这个目录下操作）
cd zhihu-crawler

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装浏览器驱动
playwright install chromium
```

## 使用

```bash
python main.py
```

程序启动后：

1. 选择爬取模式（关键词搜索 / 详情页爬取）
2. 输入关键词或知乎链接
3. 点击「开始爬取」
4. 首次使用会弹出浏览器窗口，用手机知乎 APP 扫码登录（需要等待一会儿，不是卡了）
5. 登录成功后自动开始爬取

登录状态会保存在 `browser_data/` 文件夹，后续使用无需重复登录。

## 输出文件

爬取结果保存在 `output/日期_时间/` 目录下：

| 文件 | 内容 |
|-----|------|
| `contents.csv` | 内容列表（标题、正文、链接、赞同数等） |
| `comments.csv` | 评论列表（评论内容、点赞数、IP属地等） |

CSV 文件使用 UTF-8-BOM 编码，可直接用 Excel 打开。

## 常见问题

**Q: 登录一直失败？**
A: 删除 `browser_data/` 文件夹，重新运行程序。

**Q: 搜索不到结果？**
A: 检查网络连接，确认已成功登录。

**Q: 提示找不到 zhihu.js？**
A: 确保 `libs/` 文件夹与 `main.py` 在同一目录。

## 项目结构

```
zhihu-crawler/
├── main.py           # GUI 界面入口
├── crawler.py        # 爬虫核心逻辑
├── client.py         # API 客户端
├── login.py          # 登录模块
├── extractor.py      # 数据提取器
├── models.py         # 数据模型
├── constants.py      # 常量定义
├── zhihu_sign.py     # 知乎签名算法
├── libs/
│   ├── zhihu.js      # 签名 JS 脚本
│   └── stealth.min.js
├── requirements.txt
└── README.md
```

## 免责声明

本工具仅供学习和研究使用，请遵守知乎使用协议，不得用于商业用途或大规模爬取。
