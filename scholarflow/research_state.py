from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator


class Paper(TypedDict):
    """论文数据结构"""
    title: str
    authors: List[str]
    journal: str
    year: int
    doi: Optional[str]
    pmid: Optional[str]
    impact_factor: Optional[float]
    author_position: Optional[str]
    abstract: Optional[str]
    keywords: Optional[str]
    source: str  # "pubmed" / "semantic_scholar" / "web"


class ResearchState(TypedDict):
    """LangGraph 工作流状态"""
    # 输入参数
    expert_name: str
    institution: str
    years: int

    # 步骤1: 专家论文
    raw_expert_papers: Annotated[List[Paper], operator.add]
    filtered_expert_papers: Annotated[List[Paper], operator.add]

    # 步骤2: 研究领域分析 (DeepSeek LLM 输出)
    research_areas: List[str]
    research_areas_detail: List[Dict[str, Any]]

    # 步骤3: AI论文
    ai_papers: Annotated[List[Paper], operator.add]

    # 步骤4: 合作课题
    collaboration_topics: List[Dict[str, Any]]

    # 步骤5: 输出文件
    output_dir: str
    excel_1_path: Optional[str]
    excel_2_path: Optional[str]
    ppt_path: Optional[str]

    # 人工介入控制
    current_step: str
    user_confirmed: bool
    user_feedback: Optional[str]
