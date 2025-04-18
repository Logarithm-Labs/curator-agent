from pydantic import BaseModel

from agents import Agent, RunResult

# A sub‑agent specializing in identifying risk factors or concerns.
ANALYSIS_PROMPT = """
You are a helpful assistant that analyzes the share price trends of logarithm vaults.
You are given share price histories of all logarithm vaults.
You analyze the share price trends of each vault by using linear regression and provide a summary of the trends.
Do **not** compare share prices between vaults.  
"""

class AnalysisSummary(BaseModel):
    summary: str
    """Share price trends summary for each vault."""

analysis_agent = Agent(
    name="AnalysisAgent",
    instructions=ANALYSIS_PROMPT,
    output_type=AnalysisSummary
)

async def summary_extractor(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    # The analysis agent emits an AnalysisSummary with a `summary` field.
    # We want the tool call to return just that summary text so the other agents can use it.
    return str(run_result.final_output.summary)

