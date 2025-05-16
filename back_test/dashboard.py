import re
import textwrap
from datetime import datetime

import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd
from back_test.constants import LOG_VAULT_NAMES, META_VAULT_NAME

# TradingView-like style template
TRADINGVIEW_TEMPLATE = {
    "paper_bgcolor": "#131722",
    "plot_bgcolor": "#131722",
    "font": {"color": "#D5D5D5"},
    "xaxis": {"gridcolor": "#363c4e", "title_font": {"color": "#D5D5D5"}},
    "yaxis": {"gridcolor": "#363c4e", "title_font": {"color": "#D5D5D5"}},
}

def load_vaults_performance(result_file_path: str) -> pd.DataFrame:
    """
    Loads the vaults performance from a CSV file.
    And derive the performance APR for each vault based on share price.
    APR is calculated as: (current_share_price - 1) * (365 days / days_since_start)
    """
    df = pd.read_csv(result_file_path)
    df['date'] = pd.to_datetime(df['timestamp'])
    df.sort_values(by='date', inplace=True)
    
    # Calculate share prices relative to start
    for vault_name in LOG_VAULT_NAMES:
        df[f'{vault_name}_vault_share_price'] = df[f'{vault_name}_share_price']
    df[f'{META_VAULT_NAME}_vault_share_price'] = df['net_balance'] / df['meta_vault_total_supply']
    
    # Calculate days since start for each row
    df['days_since_start'] = (df['date'] - df['date'].iloc[0]).dt.total_seconds() / (24 * 60 * 60)
    
    # Calculate APR for each point in time
    for vault_name in LOG_VAULT_NAMES:
        df[f'{vault_name}_vault_apr'] = (df[f'{vault_name}_vault_share_price']/df[f'{vault_name}_vault_share_price'].iloc[0] - 1) * (365 / df['days_since_start'])
    df[f'{META_VAULT_NAME}_vault_apr'] = (df[f'{META_VAULT_NAME}_vault_share_price']/df[f'{META_VAULT_NAME}_vault_share_price'].iloc[0] - 1) * (365 / df['days_since_start'])
    
    return df

def wrap_text(text: str, width: int = 50) -> str:
    """
    Wraps a string into multiple lines using <br> for HTML breaks.
    """
    return textwrap.fill(text, width=width).replace("\n", "<br>")


def parse_log_file(log_file_path: str) -> pd.DataFrame:
    actions = []
    last_observation = None
    last_reallocation_reasoning = ""

    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                # Update last_observation if the line contains an Observation timestamp
                if "Observation:" in line:
                    obs_match = re.search(
                        r'Observation:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line
                    )
                    if obs_match:
                        try:
                            last_observation = datetime.strptime(
                                obs_match.group(1), '%Y-%m-%d %H:%M:%S'
                            )
                        except ValueError:
                            last_observation = None
                
                # Extract both actions and reasoning from the same line
                elif "Action:" in line and "reasoning=" in line:
                    if last_observation is not None:
                        # Extract all actions from the line except reallocation
                        match = re.search(
                            r"Action:\s*(\w+),\s*Prediction:\s*vault_names=\[([^\]]+)\]\s*amounts=\[([^\]]+)\]\s*reasoning=(\"(.*?)\"|'(.*?)')",
                            line,
                            re.DOTALL
                        )

                        reallocation_math = re.search(
                            r"Action: reallocation, Prediction: action_needed=True(.*)reasoning=(\"(.*?)\"|'(.*?)')",
                            line,
                            re.DOTALL
                        )
                        
                        if match:
                            action_name = match.group(1)
                            targets = [t.strip("'\" ") for t in match.group(2).split(',')]
                            amounts = [float(a.strip()) for a in match.group(3).split(',')]
                            reasoning = match.group(4).strip()

                            actions.append({
                                "date": last_observation,
                                "action_name": action_name,
                                "targets": targets,
                                "amounts": amounts,
                                "reasoning": f"{reasoning}"
                            })
                        elif reallocation_math:
                            last_reallocation_reasoning = reallocation_math.group(2).strip()

                elif "Action: redeem_allocations" in line:
                    if last_observation is not None and last_reallocation_reasoning is not None:
                        match = re.search(
                            r"Action: redeem_allocations,\s*vault_names:\s*\[([^\]]+)\],\s*amounts:\s*\[([^\]]+)\]",
                            line,
                            re.DOTALL
                        )
                        if match:
                            targets = [t.strip("'\" ") for t in match.group(1).split(',')]
                            raw_amounts = match.group(2).split(',')
                            amounts = []
                            for a in raw_amounts:
                                # extract the number inside np.float64(...)
                                num_match = re.search(r'np\.float64\(([^)]+)\)', a)
                                if num_match:
                                    amounts.append(float(num_match.group(1)))
                            actions.append({
                                "date": last_observation,
                                "action_name": "redeem_allocations",
                                "targets": targets,
                                "amounts": amounts,
                                "reasoning": last_reallocation_reasoning
                            })
                elif "Action: allocate_assets" in line and "Prediction:" not in line:
                    if last_observation is not None:
                        match = re.search(
                            r"Action: allocate_assets,\s*vault_names:\s*\[([^\]]+)\],\s*amounts:\s*\[([^\]]+)\]",
                            line,
                            re.DOTALL
                        )
                        if match:
                            targets = [t.strip("'\" ") for t in match.group(1).split(',')]
                            raw_amounts = match.group(2).split(',')
                            amounts = []
                            for a in raw_amounts:
                                # extract the number inside np.float64(...)
                                num_match = re.search(r'np\.float64\(([^)]+)\)', a)
                                if num_match:
                                    amounts.append(float(num_match.group(1)))
                            actions.append({
                                "date": last_observation,
                                "action_name": "allocate_assets",
                                "targets": targets,
                                "amounts": amounts,
                                "reasoning": last_reallocation_reasoning
                            })

    except Exception as e:
        print(f"Error reading {log_file_path}: {e}")

    actions_df = pd.DataFrame(actions)
    if not actions_df.empty:
        actions_df["date"] = pd.to_datetime(actions_df["date"])
        actions_df["WrappedReasoning"] = actions_df["reasoning"].apply(lambda x: wrap_text(x, width=50) if x else "")
   
    return actions_df

def get_marker_y(perf_df: pd.DataFrame, date: datetime, action_type: str, vault_name: str) -> float:
    """
    Determines the y-coordinate for a marker based on the performance data.
    For allocate_assets actions, returns a value slightly below the candle's low;
    for redeem_allocations actions, slightly above the candle's high.
    """
    row = perf_df[perf_df['date'].dt.date == date.date()]
    if not row.empty:
        if action_type == 'allocate_assets':
            return row.iloc[0][f'{vault_name}_vault_apr'] * 0.9
        else:
            return row.iloc[0][f'{vault_name}_vault_apr'] * 1.1
    return None

def create_performance_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    """
    Creates a performance chart comparing APR
    Add actions to the chart
    """
    apr_data = {}
    for vault_name in LOG_VAULT_NAMES:
        apr_data[vault_name] = perf_df[f'{vault_name}_vault_apr']
    apr_data[META_VAULT_NAME] = perf_df[f'{META_VAULT_NAME}_vault_apr']


    fig = go.Figure()
    for vault_name, apr in apr_data.items():
        fig.add_trace(go.Scatter(
            x=perf_df['date'],
            y=apr,
            mode='lines',
            name=vault_name
        ))

    fig.update_layout(
        title='Vaults APR',
        xaxis_title='Date',
        yaxis_title='APR',
        **template
    )
    return fig

def create_share_price_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    share_price_data = {}
    
    for vault_name in LOG_VAULT_NAMES:
        share_price_data[vault_name] = perf_df[f'{vault_name}_vault_share_price']
    share_price_data[META_VAULT_NAME] = perf_df[f'{META_VAULT_NAME}_vault_share_price']


    fig = go.Figure()
    for vault_name, share_price in share_price_data.items():
        fig.add_trace(go.Scatter(
            x=perf_df['date'],
            y=share_price,
            mode='lines',
            name=vault_name
        ))

    fig.update_layout(
        title='Vault Share Price',
        xaxis_title='Date',
        yaxis_title='Price',
        **template
    )
    return fig

def create_allocation_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    allocation_data = {}
    for vault_name in LOG_VAULT_NAMES:
        allocation_data[vault_name] = perf_df[f'{vault_name}_shares']

    fig = go.Figure()
    for vault_name, shares in allocation_data.items():
        if vault_name != META_VAULT_NAME:
            fig.add_trace(go.Bar(
                x=perf_df['date'],
                y=shares,
                name=vault_name
            ))

    fig.update_layout(
        barmode='stack',
        title='Vault Allocations',
        xaxis_title='Date',
        yaxis_title='Shares',
        **template
    )
    return fig

def create_idle_withdrawal_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    idle_withdrawal_data = {}
    for vault_name in LOG_VAULT_NAMES:
        idle_withdrawal_data[vault_name] = perf_df[f'{vault_name}_idle_assets'] - perf_df[f'{vault_name}_pending_withdrawals']

    fig = go.Figure()
    for vault_name, idle_withdrawal in idle_withdrawal_data.items():
        fig.add_trace(go.Bar(
            x=perf_df['date'],
            y=idle_withdrawal,
            name=vault_name
        ))

    fig.update_layout(
        barmode='relative',
        title='Simulated Vault States (Idle and Pending Withdrawal Assets)',
        xaxis_title='Date',
        yaxis_title='State',
        **template
    )
    return fig

def create_action_chart(actions_df: pd.DataFrame, template: dict) -> go.Figure:
    # Flatten the list of targets and amounts into long-form
    records = []
    for idx, row in actions_df.iterrows():
        for target, amount in zip(row["targets"], row["amounts"]):
            records.append({
                "date": row["date"],
                "action_name": row["action_name"],
                "vault": target.lower(),
                "amount": amount if row["action_name"] == "allocate_assets" else -float(amount),
                "WrappedReasoning": row["WrappedReasoning"]
            })

    flattened_df = pd.DataFrame(records)
    # Get unique vaults and sorted dates
    vaults = flattened_df["vault"].unique()
    dates = sorted(flattened_df["date"].unique())

    fig = go.Figure()
    for vault in vaults:
        y_values = []
        hover_texts = []

        for date in dates:
            match = flattened_df[(flattened_df["vault"] == vault) & (flattened_df["date"] == date)]
            if not match.empty:
                amt = match["amount"].values[0]
                y_values.append(amt)
                hover_texts.append(f"Vault: {vault}<br>Date: {date.date()}<br>Amount: {amt}<br><br>{match['WrappedReasoning'].values[0]}")
            else:
                y_values.append(0)
                hover_texts.append(f"Vault: {vault}<br>Date: {date.date()}<br>Amount: 0")

        fig.add_trace(go.Bar(
            x=[str(d.date()) for d in dates],
            y=y_values,
            name=vault,
            # text=hover_texts,
            hovertext=hover_texts
        ))

    fig.update_layout(
        barmode='relative',
        title='Actions',
        xaxis_title='Date',
        yaxis_title='Actions',
        **template
    )
    return fig

def main():
    # load strategy results
    perf_df = load_vaults_performance("result.csv")

    # load agent actions
    actions_df = parse_log_file("logs.log")
    # build performance chart
    fig_allocation = create_allocation_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_idle_withdrawal = create_idle_withdrawal_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_share_price = create_share_price_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_perf = create_performance_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_actions = create_action_chart(actions_df, TRADINGVIEW_TEMPLATE)

    # run dash app
    app = dash.Dash(__name__)
    app.layout = html.Div([
        dcc.Graph(figure=fig_actions), dcc.Graph(figure=fig_share_price), dcc.Graph(figure=fig_perf), dcc.Graph(figure=fig_idle_withdrawal), dcc.Graph(figure=fig_allocation)
    ])
    # app.layout = html.Div([
    #     dcc.Graph(figure=fig_actions)
    # ])
    app.run(debug=True, host="0.0.0.0")


if __name__ == "__main__":
    main()
