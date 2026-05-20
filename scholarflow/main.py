"""LangGraph 工作流主文件 - 医工交叉论文检索与报告生成"""

import os
import sys
import json
from dotenv import load_dotenv
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from scholarflow.research_state import ResearchState
from scholarflow.nodes.search_expert import (
    search_expert_pubs,
    filter_by_author,
    analyze_research_areas,
)
from scholarflow.nodes.search_ai import search_ai_pubs
from scholarflow.nodes.generate_topics import generate_collaboration_topics
from scholarflow.nodes.generate_files import (
    generate_excel_1,
    generate_excel_2,
    generate_ppt,
)

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
os.environ["LANGCHAIN_TRACING_V2"] = "false"


def create_graph(checkpointer: Optional[SqliteSaver] = None):
    """创建 LangGraph 工作流图"""
    graph = StateGraph(ResearchState)

    # 添加节点
    graph.add_node("search_expert", search_expert_pubs)
    graph.add_node("filter_author", filter_by_author)
    graph.add_node("analyze_areas", analyze_research_areas)
    graph.add_node("search_ai", search_ai_pubs)
    graph.add_node("generate_topics", generate_collaboration_topics)
    graph.add_node("generate_excel_1", generate_excel_1)
    graph.add_node("generate_excel_2", generate_excel_2)
    graph.add_node("generate_ppt", generate_ppt)

    # 定义边
    graph.add_edge(START, "search_expert")
    graph.add_edge("search_expert", "filter_author")
    graph.add_edge("filter_author", "generate_excel_1")
    graph.add_edge("generate_excel_1", "analyze_areas")
    graph.add_edge("analyze_areas", "search_ai")
    graph.add_edge("search_ai", "generate_excel_2")
    graph.add_edge("generate_excel_2", "generate_topics")
    graph.add_edge("generate_topics", "generate_ppt")
    graph.add_edge("generate_ppt", END)

    # 编译图
    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    else:
        return graph.compile()


def cli_interactive_run():
    """CLI 交互式运行工作流"""
    print("=" * 60)
    print("ScholarFlow-Med: 医工交叉论文检索与报告生成系统")
    print("=" * 60)
    print()

    # ---- 灵活输入 ----
    expert_name = input("请输入专家姓名 (必填, 如: Lu Jin 或 路瑾): ").strip()
    if not expert_name:
        print("[错误] 专家姓名不能为空")
        return

    institution = input("请输入机构名称 (可选, 如: Peking University People's Hospital): ").strip()
    years_input = input("请输入检索年数 (可选, 默认5年): ").strip()
    years = int(years_input) if years_input.isdigit() else 5
    output_dir = input("请输入输出目录 (可选, 默认 scholarflow/output): ").strip()
    if not output_dir:
        output_dir = "scholarflow/output"

    # 支持中文名自动补全英文搜索格式
    cn_to_en = {
        "路瑾": "Lu Jin",
        "黄晓军": "Huang Xiao Jun",
        "王建祥": "Wang Jianxiang",
        "吴德沛": "Wu Depei",
        "胡豫": "Hu Yu",
        "肖志坚": "Xiao Zhijian",
        "张凤奎": "Zhang Fengkui",
        "赵永强": "Zhao Yongqiang",
        "邱录贵": "Qiu Lugui",
        "李娟": "Li Juan",
    }

    search_name = cn_to_en.get(expert_name, expert_name)

    print(f"\n专家: {expert_name} (搜索用: {search_name})")
    print(f"机构: {institution or '(未提供)'}")
    print(f"检索年数: {years}")
    print(f"输出目录: {output_dir}")
    print()

    # 初始化状态
    initial_state = {
        "expert_name": search_name,
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

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # ---- 执行工作流（带人工确认）----

    # 步骤1: 搜索专家论文
    print("\n" + "=" * 60)
    print("[步骤 1/7] 搜索专家论文...")
    print("=" * 60)
    result = search_expert_pubs(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    print(f"[完成] 找到 {len(result.get('raw_expert_papers', []))} 篇论文")

    # 作者消歧
    result = filter_by_author(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    filtered_count = len(result.get("filtered_expert_papers", []))

    # 步骤2: 生成 1.xlsx（中间产出物）
    print("\n" + "=" * 60)
    print("[步骤 2/7] 生成 1.xlsx（专家论文表格）...")
    print("=" * 60)
    result = generate_excel_1(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    print(f"[完成] 1.xlsx 已生成: {result.get('excel_1_path')}")

    # 人工确认: 审核论文列表
    print(f"\n共找到 {filtered_count} 篇论文，请审核 1.xlsx 中的论文列表。")
    choice = input("确认继续? (y=继续, n=退出, r=重新搜索): ").strip().lower()
    if choice == "n":
        print("工作流已暂停。")
        return
    elif choice == "r":
        print("请修改搜索条件后重新运行。")
        return

    # 步骤3: 分析研究领域
    print("\n" + "=" * 60)
    print("[步骤 3/7] 分析研究领域（使用 DeepSeek LLM）...")
    print("=" * 60)
    result = analyze_research_areas(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    areas = result.get("research_areas", [])
    areas_detail = result.get("research_areas_detail", [])
    print(f"[完成] 研究领域: {', '.join(areas)}")
    if areas_detail:
        for a in areas_detail:
            print(f"  - {a.get('领域中文名', a.get('领域英文名', ''))}: {a.get('论文数量', 0)}篇 ({a.get('占比', '')})")

    # 人工确认: 研究方向
    choice = input("\n研究方向是否正确? (y=继续, n=退出): ").strip().lower()
    if choice == "n":
        print("工作流已暂停。")
        return

    # 步骤4: 搜索 AI 论文
    print("\n" + "=" * 60)
    print("[步骤 4/7] 搜索 AI 论文（多轮搜索）...")
    print("=" * 60)
    result = search_ai_pubs(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    ai_count = len(result.get("ai_papers", []))
    print(f"[完成] 找到 {ai_count} 篇 AI 相关论文")

    # 步骤5: 生成 2.xlsx（中间产出物）
    print("\n" + "=" * 60)
    print("[步骤 5/7] 生成 2.xlsx（AI论文表格）...")
    print("=" * 60)
    result = generate_excel_2(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    print(f"[完成] 2.xlsx 已生成: {result.get('excel_2_path')}")

    # 人工确认: 审核 AI 论文
    choice = input(f"\nAI 论文列表是否正确? (y=继续, n=退出): ").strip().lower()
    if choice == "n":
        print("工作流已暂停。")
        return

    # 步骤6: 生成合作课题
    print("\n" + "=" * 60)
    print("[步骤 6/7] 生成合作课题（使用 DeepSeek LLM）...")
    print("=" * 60)
    result = generate_collaboration_topics(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)
    topics = result.get("collaboration_topics", [])
    print(f"[完成] 生成 {len(topics)} 个合作课题")
    for i, t in enumerate(topics[:3], 1):
        if isinstance(t, dict):
            print(f"  {i}. {t.get('title', '')}")
            print(f"     描述: {t.get('description', '')}")
            print(f"     可行性: {t.get('feasibility', '')}")

    # 人工确认: 课题方向
    choice = input("\n课题方向是否合适? (y=继续, n=退出): ").strip().lower()
    if choice == "n":
        print("工作流已暂停。")
        return

    # 步骤7: 生成 PPT
    print("\n" + "=" * 60)
    print("[步骤 7/7] 生成 out.pptx...")
    print("=" * 60)
    result = generate_ppt(initial_state)
    if "error" in result:
        print(f"[错误] {result['error']}")
        return
    initial_state.update(result)

    # ---- 输出完成 ----
    print("\n" + "=" * 60)
    print("工作流执行完成！")
    print("=" * 60)
    print(f"输出目录: {output_dir}")
    print(f"  1.xlsx: {initial_state.get('excel_1_path', '未生成')}")
    print(f"  2.xlsx: {initial_state.get('excel_2_path', '未生成')}")
    print(f"  out.pptx: {initial_state.get('ppt_path', '未生成')}")
    print()


if __name__ == "__main__":
    # 检查依赖
    try:
        import langgraph
        import openpyxl
        import pptx
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请运行: pip install langgraph openpyxl python-pptx requests python-dotenv")
        sys.exit(1)

    cli_interactive_run()
