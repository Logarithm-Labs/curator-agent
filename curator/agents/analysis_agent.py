from pydantic import BaseModel

from agents import Agent, RunResult

# A sub‑agent specializing in identifying risk factors or concerns.
ANALYSIS_PROMPT = """
You are a vault performance analyst for on-chain vaults.
You task is to analyze and summarize the performance trend of each vault based on its share price history.
You have to call the tool `get_share_price_history` only once at first to get the share price histories of all vaults.

Analysis rules:
1. Use linear regression to analyze each vault's share price trend
2. Focus on individual vault performance
3. Do not compare share prices between different vaults
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

