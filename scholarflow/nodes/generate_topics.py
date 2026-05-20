"""生成合作课题节点 - 使用 DeepSeek LLM"""

from typing import Dict, Any
from scholarflow.research_state import ResearchState


def generate_collaboration_topics(state: ResearchState) -> Dict[str, Any]:
    """生成医工交叉合作课题节点 - 使用 DeepSeek LLM"""
    research_areas = state.get("research_areas", [])
    research_areas_detail = state.get("research_areas_detail", [])
    expert_papers = state.get("filtered_expert_papers", [])
    ai_papers = state.get("ai_papers", [])

    if not research_areas:
        return {"error": "没有研究领域信息，无法生成课题"}

    # 构建上下文
    areas_text = ", ".join(research_areas[:3])

    # 专家论文摘要
    paper_summaries = []
    for i, p in enumerate(expert_papers[:10], 1):
        title = p.get("title", "")
        year = p.get("year", "")
        abstract = (p.get("abstract") or "")[:200]
        paper_summaries.append(f"{i}. [{year}] {title}: {abstract}")

    # AI 论文摘要
    ai_summaries = []
    for i, p in enumerate(ai_papers[:10], 1):
        title = p.get("title", "")
        year = p.get("year", "")
        journal = p.get("journal", "")
        ai_summaries.append(f"{i}. [{year}] {title} ({journal})")

    system_prompt = """你是一位医工交叉研究专家。请基于专家的研究领域和最新的AI论文，提出1-3个具体的合作课题方向。
请按以下 JSON 格式输出（只输出 JSON，不要其他内容）：
[
  {
    "title": "课题名称（中文，20字以内）",
    "description": "课题描述（50-100字）",
    "technologies": "涉及的技术（AI/ML/深度学习等）",
    "clinical_impact": "临床价值（20-40字）",
    "feasibility": "high/medium/low"
  }
]"""

    user_prompt = f"""专家的主要研究领域：{areas_text}

专家近年的代表性论文：
{chr(10).join(paper_summaries)}

AI/ML在血液病领域的相关研究进展：
{chr(10).join(ai_summaries)}

请基于以上信息，提出医工交叉合作课题方向，确保：
1. 结合专家的临床研究背景
2. 利用前沿AI/ML技术
3. 解决临床未满足需求"""

    try:
        from scholarflow.tools.llm_client import get_client
        llm_client = get_client()
        if llm_client:
            result = llm_client.analyze(system_prompt, user_prompt)

            import json
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                topics = json.loads(json_match.group())
            else:
                topics = json.loads(result)

            return {
                "collaboration_topics": topics,
                "current_step": "generate_topics_completed"
            }
    except Exception as e:
        print(f"  [课题生成] LLM 调用失败: {e}，使用预设模板")

    # 回退：使用预设模板
    topics = []
    area_text = " ".join(research_areas).lower()

    if "myeloma" in area_text:
        topics.append({
            "title": "基于多组学数据的多发性骨髓瘤分子分型与预后预测系统",
            "description": "整合基因组、转录组和临床数据，开发深度学习模型实现MM患者精准分型与预后预测",
            "technologies": "深度学习, 多组学整合, 生存分析",
            "clinical_impact": "提高患者分层准确性，指导个体化治疗",
            "feasibility": "high"
        })

    if "amyloidosis" in area_text:
        topics.append({
            "title": "基于病理图像与临床特征的AL淀粉样变性早期诊断AI系统",
            "description": "开发计算机视觉算法辅助病理切片判读，结合临床特征实现早期诊断",
            "technologies": "计算机视觉, 病理图像分析, 多模态融合",
            "clinical_impact": "提高早期诊断率，降低误诊率",
            "feasibility": "high"
        })

    if "car-t" in area_text or "cell therapy" in area_text:
        topics.append({
            "title": "基于数字孪生的CAR-T细胞治疗个体化方案优化",
            "description": "构建患者特异性CAR-T治疗数字孪生模型，预测治疗响应和不良反应",
            "technologies": "数字孪生, 药物代谢模型, 强化学习",
            "clinical_impact": "优化给药方案，降低CRS风险",
            "feasibility": "medium"
        })

    if len(topics) < 3:
        topics.append({
            "title": "基于大语言模型的血液病临床决策支持系统",
            "description": "利用LLM整合最新临床指南和文献，为医生提供诊断治疗建议",
            "technologies": "大语言模型, 知识图谱, RAG",
            "clinical_impact": "提高诊疗规范性，缩短诊疗周期",
            "feasibility": "high"
        })

    return {
        "collaboration_topics": topics[:3],
        "current_step": "generate_topics_completed"
    }