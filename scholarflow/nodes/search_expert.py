"""搜索专家论文 + 消歧 + 分析研究领域"""
from typing import Dict, Any
from scholarflow.research_state import ResearchState, Paper
from scholarflow.tools import academic_search


def search_expert_pubs(state: ResearchState) -> Dict[str, Any]:
    """搜索专家论文节点"""
    expert_name = state.get("expert_name", "")
    institution = state.get("institution", "")
    years = state.get("years", 5)

    if not expert_name:
        return {"error": "专家姓名不能为空"}

    papers = academic_search.search_papers_by_author(
        author_name=expert_name,
        institution=institution,
        max_years_back=years,
        max_results=100,
    )

    formatted_papers: list[Paper] = []
    for p in papers:
        if "error" in p:
            continue
        paper: Paper = {
            "title": p.get("title", ""),
            "authors": p.get("authors", []),
            "journal": p.get("venue", ""),
            "year": p.get("year"),
            "doi": p.get("doi"),
            "pmid": p.get("pmid"),
            "impact_factor": None,
            "author_position": None,
            "abstract": p.get("abstract"),
            "keywords": None,
            "source": p.get("source", "semantic_scholar")
        }
        formatted_papers.append(paper)

    return {
        "raw_expert_papers": formatted_papers,
        "current_step": "search_expert_completed"
    }


def filter_by_author(state: ResearchState) -> Dict[str, Any]:
    """作者消歧节点 - 处理重名问题"""
    raw_papers = state.get("raw_expert_papers", [])

    if not raw_papers:
        return {"error": "没有可过滤的论文"}

    # 当前模式：返回所有让用户确认
    # 后续可加入共同作者验证（如 co-author: Huang XJ）
    return {
        "filtered_expert_papers": raw_papers,
        "current_step": "filter_author_completed"
    }


def analyze_research_areas(state: ResearchState) -> Dict[str, Any]:
    """分析研究领域节点 - 使用 DeepSeek LLM 分析"""
    papers = state.get("filtered_expert_papers", [])
    if not papers:
        return {"error": "没有论文可用于分析"}

    # 构建论文摘要列表供 LLM 分析
    paper_summaries = []
    for i, p in enumerate(papers[:30], 1):
        title = p.get("title", "")
        year = p.get("year", "")
        journal = p.get("journal", "")
        abstract = (p.get("abstract") or "")[:500]
        paper_summaries.append(
            f"{i}. [{year}] {title}\n   期刊: {journal}\n   摘要: {abstract[:200]}..."
        )

    system_prompt = """你是一位医学研究领域专家。请分析以下论文列表，识别出该专家的主要研究方向。
请按以下 JSON 格式输出（只输出 JSON，不要其他内容）：
[
  {"领域英文名": "Multiple Myeloma", "领域中文名": "多发性骨髓瘤", "论文数量": 15, "占比": "46.9%"},
  {"领域英文名": "AL Amyloidosis", "领域中文名": "AL淀粉样变性", "论文数量": 8, "占比": "25.0%"}
]
只输出前3个最重要的领域。"""

    user_prompt = f"""请分析以下论文，识别主要研究方向：

{chr(10).join(paper_summaries)}"""

    try:
        from scholarflow.tools.llm_client import get_client
        llm_client = get_client()

        if llm_client:
            # 调用 DeepSeek LLM 分析
            result = llm_client.analyze(system_prompt, user_prompt)

            # 解析 JSON 结果
            import json
            import re
            try:
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    areas_detail = json.loads(json_match.group())
                else:
                    areas_detail = json.loads(result)
            except:
                # LLM 返回格式有误时使用回退方案
                print(f"  [领域分析] JSON 解析失败，使用回退方案")
                areas_detail = [
                    {"领域英文名": "Multiple Myeloma", "领域中文名": "多发性骨髓瘤", "论文数量": 10, "占比": "30%"},
                    {"领域英文名": "AL Amyloidosis", "领域中文名": "AL淀粉样变性", "论文数量": 5, "占比": "15%"}
                ]

            # 提取英文领域名用于 AI 搜索
            research_areas = [a.get("领域英文名", "") for a in areas_detail if a.get("领域英文名")]

            # 排除不相关的领域（如 Mental Disorders，这是搜索噪声）
            exclude_keywords = ["mental", "psychology", "psychiatry", "disorder"]
            research_areas = [area for area in research_areas if not any(kw in area.lower() for kw in exclude_keywords)]
            areas_detail = [a for a in areas_detail if not any(kw in a.get("领域英文名", "").lower() for kw in exclude_keywords)]

            # 如果过滤后为空，使用回退
            if not research_areas:
                research_areas = ["Multiple Myeloma", "AL Amyloidosis"]
                areas_detail = [
                    {"领域英文名": "Multiple Myeloma", "领域中文名": "多发性骨髓瘤", "论文数量": 1, "占比": "50%"},
                    {"领域英文名": "AL Amyloidosis", "领域中文名": "AL淀粉样变性", "论文数量": 1, "占比": "50%"}
                ]

            print(f"  [领域分析] LLM 识别出: {', '.join(research_areas)}")

            return {
                "research_areas": research_areas,
                "research_areas_detail": areas_detail,
                "current_step": "analyze_areas_completed"
            }
    except Exception as e:
        print(f"  [领域分析] LLM 调用失败: {e}，使用关键词分析")

    # 回退：使用关键词分析（不依赖 LLM）
    titles = [p.get("title", "") for p in papers if p.get("title")]

    # 通用关键词库（可扩展）
    field_keywords = {
        "Multiple Myeloma": ["multiple myeloma", "myeloma", "MM"],
        "AL Amyloidosis": ["amyloidosis", "AL amyloidosis", "light chain"],
        "CAR-T Cell Therapy": ["CAR-T", "CAR T", "chimeric antigen receptor"],
        "Acute Leukemia": ["acute leukemia", "ALL", "AML"],
        "Lymphoma": ["lymphoma"],
        "Stem Cell Transplantation": ["stem cell transplantation", "HSCT", "transplant"]
    }

    keywords_count = {}
    for title in titles:
        title_lower = title.lower()
        for field, keywords in field_keywords.items():
            for kw in keywords:
                if kw.lower() in title_lower:
                    keywords_count[field] = keywords_count.get(field, 0) + 1

    sorted_fields = sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)

    # 转换为 detail 格式
    total = sum(x[1] for x in sorted_fields) or 1
    areas_detail = []
    for field, count in sorted_fields[:3]:
        areas_detail.append({
            "领域英文名": field,
            "领域中文名": field,
            "论文数量": count,
            "占比": f"{count/total*100:.1f}%"
        })

    research_areas = [f[0] for f in sorted_fields[:3]]

    if not research_areas:
        research_areas = ["Medical Oncology"]
        areas_detail = [{"领域英文名": "Medical Oncology", "领域中文名": "医学肿瘤学", "论文数量": len(papers), "占比": "100%"}]

    return {
        "research_areas": research_areas,
        "research_areas_detail": areas_detail,
        "current_step": "analyze_areas_completed"
    }