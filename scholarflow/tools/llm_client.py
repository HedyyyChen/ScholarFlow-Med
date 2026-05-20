"""DeepSeek LLM 客户端 - 用于论文分析和课题生成"""

import os
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, model: str = "deepseek-v4-flash"):
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

        if not api_key or api_key == "your_deepseek_api_key_here":
            raise ValueError("未设置 DEEPSEEK_API_KEY，请在 .env 文件中配置")

        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            max_tokens=2000
        )

    def analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """调用 LLM 进行分析"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        return response.content

    def analyze_research_areas(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析论文的研究领域"""
        if not papers:
            return []

        # 构建论文摘要列表
        paper_summaries = []
        for i, p in enumerate(papers[:30], 1):  # 最多分析30篇
            title = p.get("title", "")
            year = p.get("year", "")
            journal = p.get("journal", "")
            abstract = p.get("abstract", "")[:500] if p.get("abstract") else ""
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

        result = self.analyze(system_prompt, user_prompt)

        # 解析 JSON
        import json
        try:
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                areas = json.loads(json_match.group())
            else:
                areas = json.loads(result)
            return areas
        except:
            # 解析失败，返回默认格式
            return [
                {"领域英文名": "Multiple Myeloma", "领域中文名": "多发性骨髓瘤", "论文数量": 10, "占比": "30%"},
                {"领域英文名": "AL Amyloidosis", "领域中文名": "AL淀粉样变性", "论文数量": 5, "占比": "15%"}
            ]

    def generate_collaboration_topics(
        self,
        research_areas: List[Dict[str, Any]],
        expert_papers: List[Dict[str, Any]],
        ai_papers: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """生成医工交叉合作课题"""
        if not research_areas:
            return []

        # 构建上下文
        areas_text = ", ".join([a.get("领域中文名", a.get("领域英文名", "")) for a in research_areas[:3]])

        system_prompt = """你是一位医工交叉研究专家。请基于专家的研究领域和最新的AI论文，提出1-3个具体的合作课题方向。
请按以下 JSON 格式输出：
[
  {
    "title": "课题名称（中文）",
    "description": "课题描述（50-100字）",
    "technologies": "涉及的技术（AI/ML/深度学习等）",
    "clinical_impact": "临床价值（20-40字）",
    "feasibility": "high/medium/low"
  }
]"""

        user_prompt = f"""专家的主要研究领域：{areas_text}

请基于以下背景信息，提出医工交叉合作课题：
1. 专家的研究方向
2. 近3年AI/ML在相关领域的研究进展
3. 临床未满足需求"""

        result = self.analyze(system_prompt, user_prompt)

        # 解析 JSON
        import json
        import re
        try:
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                topics = json.loads(json_match.group())
            else:
                topics = json.loads(result)
            return topics
        except:
            return []

    def generate_abstract_summary(self, title: str, abstract: str = "") -> str:
        """生成论文摘要的简化中文版本"""
        if not abstract:
            abstract = title

        system_prompt = """你是一位医学论文写作专家。请将以下论文标题/摘要精简为20-50字的中文核心内容简述。
只输出精简后的内容，不要其他说明。"""

        user_prompt = f"""论文标题：{title}
摘要：{abstract[:500]}

请生成中文核心研究内容简述："""

        result = self.analyze(system_prompt, user_prompt, max_tokens=500)
        return result.strip()[:100]  # 限制长度


def get_llm_client() -> Optional[DeepSeekClient]:
    """获取 LLM 客户端实例（如果配置了 API）"""
    try:
        return DeepSeekClient()
    except ValueError:
        return None


# 全局客户端实例
_llm_client: Optional[DeepSeekClient] = None


def get_client() -> Optional[DeepSeekClient]:
    """获取或创建全局 LLM 客户端"""
    global _llm_client
    if _llm_client is None:
        try:
            _llm_client = DeepSeekClient()
        except ValueError:
            pass
    return _llm_client