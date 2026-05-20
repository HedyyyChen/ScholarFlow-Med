"""
学术论文搜索模块 - 基于 WebSearch API

使用 Serper API (Google Search) 进行学术论文搜索。
Serper 免费版：100 次/月，有 Key 速率更高。

替代方案（如果额度用完）：
  - Tavily API (https://tavily.com/) - 专为 AI 设计
  - DuckDuckGo (无需 Key，但不稳定)

搜索策略（遵循 academic-search skill）：
  - Query expansion：同义词、缩写、医学 MeSH terms
  - 多轮查询覆盖不同 AI 技术维度
  - 结果合并去重后按相关性排序
"""

import os
import re
import time
import json
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus


# ============================================================
# WebSearch (Serper)
# ============================================================

def _serper_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """
    Serper Google Search API
    免费版 100 次/月，有 Key 1 req/s
    """
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        return []

    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": num}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("organic", []):
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        # 尝试提取 DOI
        doi = None
        doi_match = re.search(r"10\.\d{4,}/[\w\.\-/]+", link + " " + snippet)
        if doi_match:
            doi = doi_match.group()

        results.append({
            "title": title,
            "url": link,
            "snippet": snippet,
            "doi": doi,
            "source": "serper",
        })

    return results


def _tavily_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """
    Tavily Search API (https://tavily.com/)
    免费版 1000 次/月，专为 AI 设计
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return []

    url = "https://api.tavily.com/search"
    params = {"api_key": api_key, "query": query, "max_results": num}

    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("results", []):
        title = item.get("title", "")
        if not title:
            continue

        results.append({
            "title": title,
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "doi": None,
            "source": "tavily",
        })

    return results


def _duckduckgo_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """
    DuckDuckGo Instant Answer API (免费，无需 Key)
    不稳定，可能失败
    """
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    results = []
    for item in data.get("RelatedTopics", [])[:num]:
        title = item.get("Text", "")
        first_url = item.get("FirstURL", "")

        if not title or not first_url:
            continue

        results.append({
            "title": title,
            "url": first_url,
            "snippet": title,
            "doi": None,
            "source": "duckduckgo",
        })

    return results

def web_search(
    query: str,
    max_results: int = 10,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    统一 WebSearch 入口，按优先级尝试各 API。

    Args:
        query: 搜索关键词
        max_results: 最大结果数
        source: 强制指定来源 ("serper"/"tavily"/"duckduckgo")，默认自动选择
    """
    if source is None:
        # 自动选择：根据可用 Key 选择
        if os.environ.get("SERPER_API_KEY"):
            source = "serper"
        elif os.environ.get("TAVILY_API_KEY"):
            source = "tavily"
        else:
            source = "duckduckgo"

    if source == "serper":
        return _serper_search(query, max_results)
    elif source == "tavily":
        return _tavily_search(query, max_results)
    elif source == "duckduckgo":
        return _duckduckgo_search(query, max_results)
    else:
        return []


# ============================================================
# 统一搜索入口
# ============================================================

def search_academic(
    query: str,
    max_results: int = 20,
    sources: Optional[List[str]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    统一学术搜索入口。
    当前主要用 WebSearch，返回标题+URL+摘要，需要时再 deep fetch 详情。
    """
    papers = web_search(query, max_results)
    return papers


# ============================================================
# 按作者搜索专家论文
# ============================================================

def search_papers_by_author(
    author_name: str,
    institution: Optional[str] = None,
    max_years_back: int = 5,
    max_results: int = 50,
) -> List[Dict[str, Any]]:
    """
    按作者搜索论文（通过 WebSearch）。
    构造查询： author name + institution + "paper"
    """
    # 构建搜索查询
    query_parts = [author_name]
    if institution:
        query_parts.append(institution)
    query_parts.append("paper OR publication")

    query = " ".join(query_parts)

    results = web_search(query, max_results)

    # 转换为统一格式
    papers = []
    for r in results:
        title = r.get("title", "")
        if not title or "error" in title.lower():
            continue

        papers.append({
            "title": title,
            "authors": [author_name],
            "year": None,
            "venue": r.get("url", "").split("/")[2] if r.get("url") else "",
            "citation_count": 0,
            "doi": r.get("doi"),
            "pmid": None,
            "arxiv_id": None,
            "abstract": r.get("snippet"),
            "source": r.get("source", "web"),
        })

    return papers[:max_results]


# ============================================================
# AI/ML 论文搜索
# ============================================================

def generate_ai_search_queries(research_field: str, year_range: str, expert_papers: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """
    使用 LLM 为指定研究领域动态生成 AI/ML 学术搜索查询。
    LLM 不可用时使用通用模板回退。
    """
    field_en = research_field
    if "(" in research_field and ")" in research_field:
        field_en = research_field.split("(")[-1].rstrip(")").strip()

    # 尝试 LLM 生成
    try:
        from scholarflow.tools.llm_client import get_client
        llm_client = get_client()
        if llm_client:
            paper_context = ""
            if expert_papers:
                titles = [f"- {p.get('title', '')}" for p in expert_papers[:5] if p.get("title")]
                if titles:
                    paper_context = "\n\n专家代表论文（供参考领域语境）：\n" + "\n".join(titles)

            system_prompt = f"""你是一位学术搜索专家。请为以下研究领域生成 5 轮学术论文搜索查询，用于检索该领域与AI/ML结合的高水平论文。

要求：
1. 每轮查询是一个适合 Google 学术搜索的英文关键词组合
2. 用英文关键词，用引号精确匹配关键术语
3. 涵盖不同维度：machine learning、deep learning、transformer、GNN、NLP、computer vision、reinforcement learning 等
4. 根据领域特点选择最相关的 AI 技术维度
5. 可用 AND/OR 组合同义词
6. 只输出 JSON 数组，不要其他内容

输出格式：
["查询1", "查询2", "查询3", "查询4", "查询5"]"""

            user_prompt = f"研究领域：{research_field}（英文名：{field_en}）{paper_context}"
            result = llm_client.analyze(system_prompt, user_prompt, max_tokens=800)

            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group())
                if isinstance(queries, list) and len(queries) >= 3:
                    return queries[:6]
    except Exception as e:
        print(f"  [AI搜索] LLM 生成查询失败: {e}，使用通用模板")

    # 回退：通用模板
    return [
        f'machine learning "{field_en}" {year_range}',
        f'deep learning transformer "{field_en}" {year_range}',
        f'artificial intelligence diagnosis prediction "{field_en}" {year_range}',
        f'natural language processing "{field_en}" {year_range}',
        f'graph neural network "{field_en}" {year_range}',
    ]


def search_ai_papers_in_field(
    research_field: str,
    max_years_back: int = 3,
    min_citations: int = 0,
    max_results: int = 30,
    expert_papers: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    在特定领域搜索 AI/ML 相关论文 - 多轮搜索策略。
    使用 WebSearch API 查询，每个领域 5 轮查询。
    """
    current_year = 2026  # 硬编码或 datetime
    year_range = f"{current_year - max_years_back}-{current_year}"

    queries = generate_ai_search_queries(research_field, year_range, expert_papers)
    all_papers: List[Dict[str, Any]] = []

    for i, query in enumerate(queries):
        print(f"  [AI搜索] 第{i+1}/{len(queries)}轮: {query[:80]}...")

        results = web_search(query, 15)
        for r in results:
            title = r.get("title", "")
            if not title or "error" in title.lower():
                continue

            all_papers.append({
                "title": title,
                "authors": [],
                "year": None,
                "venue": r.get("url", "").split("/")[2] if r.get("url") else "",
                "citation_count": 0,
                "doi": r.get("doi"),
                "pmid": None,
                "arxiv_id": None,
                "abstract": r.get("snippet"),
                "source": r.get("source", "web"),
            })

        time.sleep(1)

    # 去重（按标题）
    seen_titles = set()
    unique = []
    for p in all_papers:
        title_key = p.get("title", "").lower().strip()[:80]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(p)

    if min_citations > 0:
        unique = [p for p in unique if p.get("citation_count", 0) >= min_citations]

    return unique[:max_results]