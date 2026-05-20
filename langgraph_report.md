## 已完成工作

### 1. 项目框架搭建
- 建立了 `scholarflow/` Python 包结构
- 创建了 conda 环境 `scholarflow`（Python 3.11），安装了所有依赖
- 配置了 DeepSeek LLM 客户端（`scholarflow/tools/llm_client.py`）

### 2. 工作流节点开发
| 文件 | 功能 | 状态 |
|------|------|------|
| `research_state.py` | LangGraph 工作流状态定义 | 完成 |
| `tools/llm_client.py` | DeepSeek LLM 客户端（deepseek-v4-flash） | 完成 |
| `nodes/search_expert.py` | 搜索专家论文 + 作者消歧 + 研究领域分析 | 完成 |
| `nodes/search_ai.py` | 多轮策略搜索 AI 论文 | 完成 |
| `nodes/generate_topics.py` | DeepSeek LLM 生成合作课题 | 完成 |
| `nodes/generate_files.py` | Excel/PPT 生成（按 Workbuddy 格式） | 完成 |
| `tools/academic_search.py` | 学术搜索工具封装 | 存在问题（见下） |
| `main.py` | CLI 交互式工作流主程序 | 完成 |

### 3. 设计的流程
```
输入专家信息（仅姓名必填）
   -> 搜索专家论文
   -> 生成 1.xlsx（中间产出物）
   -> [用户确认] 审核论文列表
   -> 分析研究领域（调用 DeepSeek LLM）
   -> [用户确认] 确认研究方向
   -> 搜索 AI 论文（多轮策略）
   -> 生成 2.xlsx（中间产出物）
   -> [用户确认] 审核 AI 论文
   -> 生成合作课题（调用 DeepSeek LLM）
   -> [用户确认] 确认课题方向
   -> 生成 out.pptx
```

### 4. 功能特点
- **LLM 集成**：使用 deepseek-v4-flash 调用 DeepSeek API 进行：
     - 论文研究领域分析（输出英文领域名，便于搜索 AI 论文）
     - 中文核心内容简述生成（填充 Excel "核心研究内容简述" 列）
     - 合作课题方向生成
- **灵活输入**：支持输入中文名自动转换为拼音搜索
- **中间产出物**：Excel 作为中间文件，用户可审核后决定是否继续
- **AI 论文多轮搜索**：每个研究领域执行 5 轮搜索（machine learning、deep learning、transformer、GNN 等技术 x 领域），同时查询 Semantic Scholar + PubMed

### 5. Excel 格式（参考 Workbuddy）
- **1.xlsx（专家论文）**：序号、论文标题、期刊、20xx IF、发表年份、作者排位、核心研究内容简述、DOI
- **2.xlsx（AI 论文）**：序号、论文标题、期刊、20xx IF、发表年份、作者排位、核心研究内容简述、DOI、研究领域、AI技术

---

## 当前问题

### 关键阻塞问题

**1. 网络 SSL 错误 - 无法访问学术 API**
```
SSLError: UNEXPECTED_EOF_WHILE_READING
```
- Semantic Scholar API (`api.semanticscholar.org`) 和 PubMed API (`eutils.ncbi.nlm.nih.gov`) 均无法连接
- 猜测是 Windows 环境下的 SSL 证书问题，尝试过 `verify=False` 仍失败
- **影响**：整个搜索流程无法运行

**2. Academic Search Skill 缺失**
- 项目中没有 `academic-search` skill（`.agents/skills/` 下没有此文件）
- Workbuddy 能用此 skill 是因为它是 Workbuddy 内置的
- **影响**：无法使用 Workbuddy 的学术搜索能力

### 次要问题

**3. DeepSeek 模型选择**
- 当前使用 `deepseek-v4-flash`（测试用，节省 token）
- 后续需要切换为 `deepseek-v4-pro`（需要修改 `scholarflow/tools/llm_client.py` 第12行的默认参数）

**4. 网络代理配置**
- 项目中未配置代理环境变量
- 如果需要代理访问学术 API，需要在 `.env` 文件中添加：
     ```
     HTTP_PROXY=http://proxy:port
     HTTPS_PROXY=http://proxy:port
     ```

---

## 建议下一步方案

### 方案 A（推荐）：手动提供数据
1. 用户提供路瑾教授的论文列表（从 PubMed 或其他地方导出）
2. 我将数据导入工作流，跳过搜索步骤，直接测试：
     - DeepSeek LLM 分析研究领域
     - DeepSeek LLM 生成合作课题
     - Excel/PPT 生成

### 方案 B：使用 WebSearch
1. 通过 Claude 的 WebSearch 工具搜索论文数据
2. 将数据保存为本地 JSON 文件
3. 修改代码从本地文件读取

### 方案 C：解决网络问题
1. 配置代理访问学术 API
2. 或解决 SSL 证书问题
3. 重新测试完整工作流

---

## 文件清单

```
ScholarFlow-Med/
├── scholarflow/
│     ├── __init__.py
│     ├── main.py                     # 工作流主程序（CLI交互式）
│     ├── research_state.py           # LangGraph 状态定义
│     ├── requirements.txt            # Python 依赖
│     ├── setup.py                    # 包配置
│     ├── .env                        # DeepSeek API Key
│     ├── tools/
│     │     ├── __init__.py
│     │     ├── llm_client.py           # DeepSeek LLM 客户端
│     │     └── academic_search.py      # 学术搜索（当前不可用）
│     ├── nodes/
│     │     ├── __init__.py
│     │     ├── search_expert.py        # 搜索专家论文节点
│     │     ├── search_ai.py            # 搜索AI论文节点
│     │     ├── generate_topics.py      # 生成合作课题节点
│     │     └── generate_files.py       # 生成Excel/PPT节点
│     └── test_workflow.py            # 测试脚本
├── report.md                       # 前期调研报告
├── langgraph_report.md             # 本报告
├── workbuddy交付物/               # Workbuddy 产出（参考）
├── gemini交付物/                   # Gemini 产出（参考）
└── .agents/skills/                # LangChain skills
```
