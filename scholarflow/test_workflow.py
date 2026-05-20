"""测试脚本 - 直接调用工作流"""

import os
import sys

# 设置环境
os.chdir("D:/yzzw/demon/agent/ScholarFlow-Med")
sys.path.insert(0, "D:/yzzw/demon/agent/ScholarFlow-Med")

from dotenv import load_dotenv
load_dotenv("D:/yzzw/demon/agent/ScholarFlow-Med/scholarflow/.env")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from scholarflow.nodes.search_expert import search_expert_pubs, filter_by_author, analyze_research_areas
from scholarflow.nodes.search_ai import search_ai_pubs
from scholarflow.nodes.generate_topics import generate_collaboration_topics
from scholarflow.nodes.generate_files import generate_excel_1, generate_excel_2, generate_ppt
from scholarflow.tools import academic_search


def test_workflow():
    output_dir = "scholarflow/output"
    os.makedirs(output_dir, exist_ok=True)

    expert_name = "Lu Jin"
    institution = "Peking University People's Hospital"
    years = 5

    # 先测试搜索
    print("\n[Debug] 测试直接搜索...")
    papers = academic_search.search_papers_by_author(
        author_name=expert_name,
        institution=institution,
        max_years_back=years,
        max_results=50
    )
    print(f"  直接搜索返回: {len(papers)} 篇")
    for p in papers[:3]:
        print(f"    - {p.get('title', 'NO TITLE')[:60]}")

    state = {
        "expert_name": expert_name,
        "institution": institution,
        "years": years,
        "raw_expert_papers": [],
        "filtered_expert_papers": [],
        "research_areas": [],
        "research_areas_detail": [],
        "ai_papers": [],
        "collaboration_topics": [],
        "output_dir": output_dir,
        "excel_1_path": None,
        "excel_2_path": None,
        "ppt_path": None,
        "current_step": "initialized",
        "user_confirmed": False,
        "user_feedback": None,
    }

    # Step 1: 搜索专家论文
    print("\n[Step 1] 搜索专家论文...")
    result = search_expert_pubs(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] 找到 {len(state['raw_expert_papers'])} 篇论文")

    # Step 2: 作者消歧
    print("\n[Step 2] 作者消歧...")
    result = filter_by_author(state)
    state.update(result)
    print(f"  [完成] 过滤后 {len(state['filtered_expert_papers'])} 篇论文")

    # Step 3: 生成 1.xlsx
    print("\n[Step 3] 生成 1.xlsx...")
    result = generate_excel_1(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] {state['excel_1_path']}")

    # Step 4: 分析研究领域 (LLM)
    print("\n[Step 4] 分析研究领域 (DeepSeek LLM)...")
    result = analyze_research_areas(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] 领域: {state['research_areas']}")
    for a in state.get('research_areas_detail', []):
        print(f"    - {a.get('领域中文名', a.get('领域英文名'))}: {a.get('论文数量')}篇 ({a.get('占比')})")

    # Step 5: 搜索 AI 论文
    print("\n[Step 5] 搜索 AI 论文...")
    result = search_ai_pubs(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] 找到 {len(state['ai_papers'])} 篇 AI 论文")

    # Step 6: 生成 2.xlsx
    print("\n[Step 6] 生成 2.xlsx...")
    result = generate_excel_2(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] {state['excel_2_path']}")

    # Step 7: 生成合作课题 (LLM)
    print("\n[Step 7] 生成合作课题 (DeepSeek LLM)...")
    result = generate_collaboration_topics(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] 生成 {len(state['collaboration_topics'])} 个课题")
    for t in state['collaboration_topics'][:2]:
        if isinstance(t, dict):
            print(f"    - {t.get('title')}: {t.get('feasibility')}")

    # Step 8: 生成 PPT
    print("\n[Step 8] 生成 PPT...")
    result = generate_ppt(state)
    if "error" in result:
        print(f"  [错误] {result['error']}")
        return
    state.update(result)
    print(f"  [完成] {state['ppt_path']}")

    print("\n" + "=" * 50)
    print("工作流测试完成!")
    print(f"输出目录: {output_dir}")
    print("=" * 50)


if __name__ == "__main__":
    test_workflow()