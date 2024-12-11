from hyperliquid.info import Info
from hyperliquid.utils import constants
import streamlit as st
import pandas as pd
from datetime import datetime
import hmac

info = Info("https://api.hyperliquid.xyz", skip_ws=True)

addresses = {
    "Main Account-72a9": st.secrets['main_account'],
    "Dust-41d5": st.secrets['dust'],
    "Hold-aff3": st.secrets['hold'],
    "Vault-ba36": st.secrets['vault']
}

# fetching and storing spot prices and token mappings
spot_meta_data = info.spot_meta_and_asset_ctxs()
token_index_mapping = {token['tokens'][0]: token['name']
                       for token in spot_meta_data[0]['universe']}
# token index mapping for USDC
token_index_mapping[0] = '@0'
spot_prices = info.all_mids()
# spot price for USDC
spot_prices['@0'] = '1.00'


def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

st.set_page_config(page_title="Hyperliquid Positions",
                   page_icon='🐘', layout='wide')
st.title("Hyperliquid Positions")
st.write(f"Date and Time: {datetime.now()} UTC")
ids = addresses.keys()
tabs = st.tabs(ids)
for id, tab in zip(ids, tabs):
    name = id
    address = addresses[id]
    tab.header(name)
    perps_user_state = info.user_state(address)
    spot_user_state = info.spot_user_state(address)
    summary = perps_user_state['crossMarginSummary']
    perps_account_value = float(summary['accountValue'])
    column1, column2, column3 = tab.columns(3)
    perps_total_margin_used = float(summary['totalMarginUsed'])
    perps_total_pos_value = float(summary['totalNtlPos'])
    column1.write(f"**Account Value**: ${perps_account_value:,.2f}")
    column1.write(
        f"**Total Notional Position**: ${perps_total_pos_value:,.2f}")
    column1.write(f"**Total Margin Used**: ${perps_total_margin_used:,.2f}")
    if perps_user_state['assetPositions'] == []:
        tab.write(f"**No Perp Positions open**")
    else:
        positions = [{'Coin': position['position']['coin'],
                      'Entry Position': float(position['position']['entryPx']),
                      'Position Value': float(position['position']['positionValue']),
                      'Unrealized Pnl': float(position['position']['unrealizedPnl']),
                      'Invested Value': (float(position['position']['positionValue']) - float(position['position']['unrealizedPnl'])),
                      'Liquidation Price': float(position['position']['liquidationPx']) if position['position']['liquidationPx'] is not None else float('nan'),
                      'All Time Funding': float(position['position']['cumFunding']['allTime'])
                      } for position in perps_user_state['assetPositions']]
        perps_positions_df = pd.DataFrame(positions)
        perps_total_pnl = perps_positions_df['Unrealized Pnl'].sum()
        perps_total_funding = perps_positions_df['All Time Funding'].sum()
        column2.write(f"**Total Unrealized PnL**: ${perps_total_pnl:,.2f}")
        column2.write(f"**Total Funding**: ${perps_total_funding:,.2f}")
        column2.write(
            f"**Leverage**: {(perps_total_pos_value/perps_account_value):,.2f}")
        perps_init_balance = perps_account_value - perps_total_pnl
        perps_pnl_pct = (
            (perps_account_value - perps_init_balance) / perps_init_balance) * 100
        column3.write(f"**Initial Balance**: {perps_init_balance:,.2f}")
        column3.write(f"**PnL %**: {perps_pnl_pct:,.2f}")
        tab.subheader(f"**Perp Positions**: {len(perps_positions_df):,}")
        tab.dataframe(perps_positions_df,
                      use_container_width=True, hide_index=True)
    if spot_user_state['balances'] == []:
        tab.write(f"No Spot balances")
    else:
        # mapping spot positions to prices
        for spot_token in spot_user_state['balances']:
            token_id = spot_token['token']
            spot_token['price'] = spot_prices[token_index_mapping[token_id]]
        spot_positions_df = pd.DataFrame(spot_user_state['balances'])
        spot_positions_df['usd_value'] = spot_positions_df['total'].astype(float) * \
            spot_positions_df['price'].astype(float)
        spot_positions_df.drop(columns=['token', 'hold'], inplace=True)
        spot_positions_df.sort_values(
            by='usd_value', ascending=False, inplace=True)  # Sort in place
        tab.subheader(f"**Spot Positions**: {len(spot_positions_df):,}")
        tab.dataframe(spot_positions_df,
                      use_container_width=True, hide_index=True)
