import re
import textwrap
from datetime import datetime

import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd

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
    And derive the performance APY for each vault based on share price.
    APY is calculated as: (current_share_price - 1) * (365 days / days_since_start)
    """
    df = pd.read_csv(result_file_path)
    df['date'] = pd.to_datetime(df['timestamp'])
    df.sort_values(by='date', inplace=True)
    
    # Calculate share prices relative to start
    df['meta_vault_share_price'] = df['meta_vault_balance'] / df['meta_vault_balance'].iloc[0]
    df['eth_share_price'] = df['eth_share_price'] / df['eth_share_price'].iloc[0]
    df['btc_share_price'] = df['btc_share_price'] / df['btc_share_price'].iloc[0]
    df['doge_share_price'] = df['doge_share_price'] / df['doge_share_price'].iloc[0]
    df['pepe_share_price'] = df['pepe_share_price'] / df['pepe_share_price'].iloc[0]
    
    # Calculate days since start for each row
    df['days_since_start'] = (df['date'] - df['date'].iloc[0]).dt.total_seconds() / (24 * 60 * 60)
    
    # Calculate APY for each point in time
    df['meta_vault_apy'] = (df['meta_vault_share_price'] - 1) * (365 / df['days_since_start'])
    df['eth_vault_apy'] = (df['eth_share_price'] - 1) * (365 / df['days_since_start'])
    df['btc_vault_apy'] = (df['btc_share_price'] - 1) * (365 / df['days_since_start'])
    df['doge_vault_apy'] = (df['doge_share_price'] - 1) * (365 / df['days_since_start'])
    df['pepe_vault_apy'] = (df['pepe_share_price'] - 1) * (365 / df['days_since_start'])
    
    return df

def wrap_text(text: str, width: int = 50) -> str:
    """
    Wraps a string into multiple lines using <br> for HTML breaks.
    """
    return textwrap.fill(text, width=width).replace("\n", "<br>")


def parse_log_file(log_file_path: str) -> pd.DataFrame:
    """
    Parses a log file to extract agent actions. For each action, the timestamp of
    the last observation is used. Returns a DataFrame of actions with the following format:
    [{
        "date": last observation before the action
        "actions": [{
            "action_name": "allocate_assets" / "redeem_allocations"
            "targets": vault_names list
            "amounts": amounts list
        }]
        "reasoning": reasoning string
    }]
    """
    actions = []
    last_observation = None

    try:
        with open(log_file_path, 'r') as f:
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
                elif "actions=[" in line and "reasoning=" in line:
                    if last_observation is not None:
                        # Extract all actions from the line
                        action_matches = re.finditer(
                            r"Action\(name='(\w+)', vault_names=\[([^\]]+)\], amounts=\[([^\]]+)\]\)",
                            line
                        )
                        
                        action_list = []
                        for match in action_matches:
                            action_name = match.group(1)
                            targets = [t.strip("' ") for t in match.group(2).split(',')]
                            amounts = [float(amt.strip()) for amt in match.group(3).split(',')]
                            
                            action_list.append({
                                "action_name": action_name,
                                "targets": targets,
                                "amounts": amounts
                            })

                        # Extract reasoning
                        reasoning_match = re.search(r"reasoning=\"(.*?)\"", line)
                        reasoning = reasoning_match.group(1) if reasoning_match else None

                        if action_list and reasoning:  # Only add if we found both actions and reasoning
                            actions.append({
                                "date": last_observation,
                                "actions": action_list,
                                "reasoning": reasoning
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
            return row.iloc[0][f'{vault_name}_vault_apy'] * 0.9
        elif action_type == 'redeem_allocations':
            return row.iloc[0][f'{vault_name}_vault_apy'] * 1.1
    return None

def create_performance_chart(perf_df: pd.DataFrame, actions_df: pd.DataFrame, template: dict) -> go.Figure:
    """
    Creates a performance chart comparing APY
    Add actions to the chart
    """

    btc_apy = perf_df['btc_vault_apy']
    eth_apy = perf_df['eth_vault_apy']
    doge_apy = perf_df['doge_vault_apy']
    pepe_apy = perf_df['pepe_vault_apy']
    meta_vault_apy = perf_df['meta_vault_apy']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=btc_apy,
        mode='lines',
        name='BTC'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=eth_apy,
        mode='lines',
        name='ETH'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=doge_apy,
        mode='lines',
        name='DOGE'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=pepe_apy,
        mode='lines',
        name='PEPE'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=meta_vault_apy,
        mode='lines',
        name='Meta Vault'
    ))
    
    if not actions_df.empty:
        for index, row in actions_df.iterrows():
            for action in row['actions']:
                for i, (target, amount) in enumerate(zip(action['targets'], action['amounts'])):
                    y = get_marker_y(perf_df, row['date'], action['action_name'], target)
                    action_name = action['action_name']
                    fig.add_trace(go.Scatter(
                        x=[row['date']],
                        y=[y],
                        mode='markers',
                        marker=dict(symbol='triangle-up' if action_name == 'allocate_assets' else 'triangle-down', color='green' if action_name == 'allocate_assets' else 'red', size=12),
                        name=f'{action_name} {target} {amount}',
                        text=row['WrappedReasoning']
                    ))

    fig.update_layout(
        title='Vaults Performance',
        xaxis_title='Date',
        yaxis_title='APY',
        **template
    )
    return fig

def main():
    # load strategy results
    perf_df = load_vaults_performance("result.csv")

    # load agent actions
    actions_df = parse_log_file("runs/CuratorStrategy/3c1ae58e-80af-4c9f-9959-d26a072d9835/logs/logs.log")

    # build performance chart
    fig_perf = create_performance_chart(perf_df, actions_df, TRADINGVIEW_TEMPLATE)

    # run dash app
    app = dash.Dash(__name__)
    app.layout = html.Div([
        dcc.Graph(figure=fig_perf)
    ])
    app.run(debug=True)


if __name__ == "__main__":
    main()
