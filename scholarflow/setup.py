from setuptools import setup, find_packages

setup(
    name="scholarflow",
    version="0.1.0",
    description="医工交叉论文检索与报告生成系统",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "langgraph>=0.2.0",
        "langgraph-checkpoint-sqlite>=0.1.0",
        "langchain-core>=0.3.0",
        "langchain-openai>=0.2.0",
        "openpyxl>=3.1.0",
        "python-pptx>=0.6.23",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "scholarflow=scholarflow.main:cli_interactive_run",
        ],
    },
)
