from pydantic import BaseModel

from agents import Agent, RunResult

# A sub‑agent specializing in identifying risk factors or concerns.
ANALYSIS_PROMPT = """
You are an on-chain vault performance analyst, supporting decision-making of other AI agents.
You are given a list of vault names to analyse with a look-back window length and the forecast horizon.  
Your task is to analyze the share price history and provide the following information for each vault:
- Trend direction
- Trend strength
- Confidence level
- Forecasted share price
- Justification

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
    model="o4-mini"
)

def summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    # The analysis agent emits an AnalysisSummary with a `summary` field.
    # We want the tool call to return just that summary text so the other agents can use it.
    return str(run_result.final_output.summary)

