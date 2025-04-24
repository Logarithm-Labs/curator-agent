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
    df['meta_vault_share_price'] = df['net_balance'] / df['meta_vault_total_supply']
    
    # Calculate days since start for each row
    df['days_since_start'] = (df['date'] - df['date'].iloc[0]).dt.total_seconds() / (24 * 60 * 60)
    
    # Calculate APR for each point in time
    df['meta_vault_apr'] = (df['meta_vault_share_price'] - 1) * (365 / df['days_since_start'])
    df['eth_vault_apr'] = (df['eth_share_price'] - 1) * (365 / df['days_since_start'])
    df['btc_vault_apr'] = (df['btc_share_price'] - 1) * (365 / df['days_since_start'])
    df['doge_vault_apr'] = (df['doge_share_price'] - 1) * (365 / df['days_since_start'])
    df['pepe_vault_apr'] = (df['pepe_share_price'] - 1) * (365 / df['days_since_start'])

    # Calculate APY for each point in time
    df['meta_vault_apy'] = (1 + df['meta_vault_apr'] / 365) ** 365 - 1
    df['eth_vault_apy'] = (1 + df['eth_vault_apr'] / 365) ** 365 - 1
    df['btc_vault_apy'] = (1 + df['btc_vault_apr'] / 365) ** 365 - 1
    df['doge_vault_apy'] = (1 + df['doge_vault_apr'] / 365) ** 365 - 1
    df['pepe_vault_apy'] = (1 + df['pepe_vault_apr'] / 365) ** 365 - 1
    
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
                elif "Action:" in line and "reasoning=" in line:
                    if last_observation is not None:
                        # Extract all actions from the line
                        match = re.search(
                            r"Action:\s*(\w+),\s*Prediction:\s*vault_names=\[([^\]]+)\]\s*amounts=\[([^\]]+)\]\s*reasoning=[',\"](.*?)['\"]",
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
        else:
            return row.iloc[0][f'{vault_name}_vault_apy'] * 1.1
    return None

def create_performance_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
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

    fig.update_layout(
        title='Vaults APY',
        xaxis_title='Date',
        yaxis_title='APY',
        **template
    )
    return fig

def create_share_price_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    btc_share_price = perf_df['btc_share_price']
    eth_share_price = perf_df['eth_share_price']
    doge_share_price = perf_df['doge_share_price']
    pepe_share_price = perf_df['pepe_share_price']
    meta_vault_share_price = perf_df['meta_vault_share_price']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=btc_share_price,
        mode='lines',
        name='BTC'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=eth_share_price,
        mode='lines',
        name='ETH'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=doge_share_price,
        mode='lines',
        name='DOGE'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=pepe_share_price,
        mode='lines',
        name='PEPE'
    ))
    fig.add_trace(go.Scatter(
        x=perf_df['date'],
        y=meta_vault_share_price,
        mode='lines',
        name='Meta Vault'
    ))

    fig.update_layout(
        title='Vault Share Prices',
        xaxis_title='Date',
        yaxis_title='Price',
        **template
    )
    return fig

def create_allocation_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    btc_shares = perf_df['btc_shares']
    eth_shares = perf_df['eth_shares']
    doge_shares = perf_df['doge_shares']
    pepe_shares = perf_df['pepe_shares']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=btc_shares,
        name='BTC'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=eth_shares,
        name='ETH'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=doge_shares,
        name='DOGE'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=pepe_shares,
        name='PEPE'
    ))

    fig.update_layout(
        barmode='stack',
        title='Vaults Allocations',
        xaxis_title='Date',
        yaxis_title='Shares',
        **template
    )
    return fig

def create_idle_withdrawal_chart(perf_df: pd.DataFrame, template: dict) -> go.Figure:
    btc_idle_assets = perf_df['btc_idle_assets']
    eth_idle_assets = perf_df['eth_idle_assets']
    doge_idle_assets = perf_df['doge_idle_assets']
    pepe_idle_assets = perf_df['pepe_idle_assets']
    btc_pending_withdrawals = perf_df['btc_pending_withdrawals']
    eth_pending_withdrawals = perf_df['eth_pending_withdrawals']
    doge_pending_withdrawals = perf_df['doge_pending_withdrawals']
    pepe_pending_withdrawals = perf_df['pepe_pending_withdrawals']

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=btc_idle_assets - btc_pending_withdrawals,
        name='BTC'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=eth_idle_assets - eth_pending_withdrawals,
        name='ETH'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=doge_idle_assets - doge_pending_withdrawals,
        name='DOGE'
    ))
    fig.add_trace(go.Bar(
        x=perf_df['date'],
        y=pepe_idle_assets - pepe_pending_withdrawals,
        name='PEPE'
    ))

    fig.update_layout(
        barmode='relative',
        title='Vault States',
        xaxis_title='Date',
        yaxis_title='Idles & Withdrawals',
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
        barmode='stack',
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
    actions_df = parse_log_file("runs/CuratorStrategy/da0055b4-78b8-4855-ad48-5207b32476b1/logs/logs.log")

    # build performance chart
    fig_allocation = create_allocation_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_idle_withdrawal = create_idle_withdrawal_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_share_price = create_share_price_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_perf = create_performance_chart(perf_df, TRADINGVIEW_TEMPLATE)
    fig_actions = create_action_chart(actions_df, TRADINGVIEW_TEMPLATE)

    # run dash app
    app = dash.Dash(__name__)
    app.layout = html.Div([
        dcc.Graph(figure=fig_share_price), dcc.Graph(figure=fig_idle_withdrawal), dcc.Graph(figure=fig_perf), dcc.Graph(figure=fig_allocation), dcc.Graph(figure=fig_actions)
    ])
    # app.layout = html.Div([
    #     dcc.Graph(figure=fig_actions)
    # ])
    app.run(debug=True)


if __name__ == "__main__":
    main()
