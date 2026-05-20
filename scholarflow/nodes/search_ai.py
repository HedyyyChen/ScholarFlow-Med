"""搜索AI论文节点 - 多轮策略"""
from typing import Dict, Any
from scholarflow.research_state import ResearchState, Paper
from scholarflow.tools import academic_search


def search_ai_pubs(state: ResearchState) -> Dict[str, Any]:
    """搜索AI相关论文节点 - 多轮搜索"""
    research_areas = state.get("research_areas", [])
    expert_papers = state.get("filtered_expert_papers", [])

    if not research_areas:
        return {"error": "没有确定研究领域，无法搜索AI论文"}

    all_ai_papers = []

    for area in research_areas[:3]:
        print(f"  [AI搜索] 领域: {area}")
        papers = academic_search.search_ai_papers_in_field(
            research_field=area,
            max_years_back=3,
            min_citations=0,
            max_results=25,
            expert_papers=expert_papers,
        )
        print(f"  [AI搜索] {area} 中找到 {len(papers)} 篇")
        all_ai_papers.extend(papers)

    formatted_papers: list[Paper] = []
    for p in all_ai_papers:
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

    # 按年份倒序排列
    formatted_papers.sort(key=lambda x: x.get("year", 0) or 0, reverse=True)

    print(f"  [AI搜索] 总计去重后: {len(formatted_papers)} 篇")

    return {
        "ai_papers": formatted_papers[:50],
        "current_step": "search_ai_completed"
    }