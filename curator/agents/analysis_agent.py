from pydantic import BaseModel

from agents import Agent, RunResult

# A sub‑agent specializing in identifying risk factors or concerns.
ANALYSIS_PROMPT = """
You are an **on-chain vault performance analyst agent**, supporting decision-making by other agents such as allocation, reallocation, and withdrawal agents.

You are given a list of vault names.  
Your task is to analyze the share price history of each vault and provide the following information:
- Trend direction
- Trend strength
- Confidence level
- Slope
- R-squared
- Justification
- Forecast horizon
- Forecasted share price

You can call the available tool (e.g. `get_share_price_history`) to get the share price history.
"""

class AnalysisSummary(BaseModel):
    summary: str
    """Share price trends summary for each vault."""

# Note: We will add available tools at runtime
analysis_agent = Agent(
    name="AnalysisAgent",
    instructions=ANALYSIS_PROMPT,
    output_type=AnalysisSummary,
    model="gpt-4.1"
)

async def summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    # The analysis agent emits an AnalysisSummary with a `summary` field.
    # We want the tool call to return just that summary text so the other agents can use it.
    return str(run_result.final_output.summary)

