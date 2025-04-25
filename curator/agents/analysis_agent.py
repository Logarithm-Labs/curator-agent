from pydantic import BaseModel

from agents import Agent, RunResult

# A sub‑agent specializing in identifying risk factors or concerns.
ANALYSIS_PROMPT = """
You are a vault performance analyst for on-chain vaults.
You are given a list of vault names to analyze.
You task is to analyze and summarize the performance trend of each given vault based on its share price history.
You can call the available tool (e.g. get_share_price_history) to get all the share price history.

Analysis rules:
1. Use linear regression to analyze each vault's share price trend
2. Do not compare share prices between different vaults
"""

class AnalysisSummary(BaseModel):
    summary: str
    """Share price trends summary for each vault."""

# Note: We will add available tools at runtime
analysis_agent = Agent(
    name="AnalysisAgent",
    instructions=ANALYSIS_PROMPT,
    output_type=AnalysisSummary,
    model="gpt-4o-2024-08-06"
)

async def summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    # The analysis agent emits an AnalysisSummary with a `summary` field.
    # We want the tool call to return just that summary text so the other agents can use it.
    return str(run_result.final_output.summary)

