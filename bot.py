import pandas as pd
import datetime
import streamlit as st
from kucoin.client import Market

# === Streamlit UI ===
st.set_page_config(page_title="KuCoin Grid Trading Backtest", layout="wide")
st.title("📉 KuCoin Grid Trading Backtest")
st.write("Simulate a grid trading strategy using historical KuCoin data.")

st.markdown("""
### ℹ️ What is Grid Trading?

Grid trading is an automated strategy that places buy and sell orders at fixed price levels.  
It buys when the price drops and sells when it rises, aiming to profit from market fluctuations  
without needing to predict direction.
""")

# === Layout: Left for controls, right for dates ===
left, right = st.columns([2, 1])

# Static list of trading pairs (can be expanded)
available_pairs = [
    "DOGE-USDT", "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"
]

with left:
    SYMBOL = st.selectbox("Choose Trading Pair", available_pairs)
    LOWER_BOUND = st.number_input("Lower Bound Price", value=0.16, step=0.001)
    UPPER_BOUND = st.number_input("Upper Bound Price", value=0.18, step=0.001)
    GRID_SPACING = st.number_input("Grid Spacing ($)", value=0.02, step=0.001)
    TRADE_AMOUNT_USDT = st.number_input("Amount per Trade ($)", value=100, step=10)

with right:
    start_date = st.date_input("Start Date", datetime.date(2025, 3, 1))
    end_date = st.date_input("End Date", datetime.date(2025, 6, 1))

# === Run Button ===
run_bot = st.button("Run Simulation")

if run_bot:
    if GRID_SPACING <= 0:
        st.error("Grid Spacing must be greater than 0.")
        st.stop()

    try:
        market = Market()
        st.success("✅ Connected to KuCoin Market API")
    except Exception as e:
        st.error(f"❌ KuCoin connection failed: {e}")
        st.stop()

    # === Fetch historical data ===
    st.write("📡 Fetching historical price data...")
    try:
        kline_data = market.get_kline(
            SYMBOL,
            '1hour',
            startAt=int(datetime.datetime.combine(start_date, datetime.time.min).timestamp()),
            endAt=int(datetime.datetime.combine(end_date, datetime.time.min).timestamp())
        )
    except Exception as e:
        st.error(f"❌ Failed to fetch Kline data: {e}")
        st.stop()

    if not kline_data:
        st.warning("No price data returned. Try a different date range or pair.")
        st.stop()

    # Process Kline data into DataFrame
    df_all = pd.DataFrame(kline_data, columns=[
        'Time', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover'
    ])
    df_all['datetime'] = pd.to_datetime(df_all['Time'], unit='s')
    df_all.set_index('datetime', inplace=True)
    df_all['price'] = df_all['Close'].astype(float)
    df_prices = df_all[['price']].sort_index()

    # === Generate Grid Levels ===
    grid_levels = []
    level = LOWER_BOUND
    while level <= UPPER_BOUND:
        grid_levels.append(round(level, 4))
        level += GRID_SPACING

    # === Grid Trading Simulation ===
    open_positions = []
    trade_log = []
    total_profit = 0

    def is_already_bought(level):
        return any(pos['buy_price'] == level for pos in open_positions)

    for time, price in df_prices['price'].items():
        now = time

        # SELL if price reached above buy+spacing
        for position in open_positions[:]:
            sell_price = position['buy_price'] + GRID_SPACING
            if price >= sell_price:
                profit = GRID_SPACING * TRADE_AMOUNT_USDT / position['buy_price']
                total_profit += profit
                trade_log.append([now, 'SELL', sell_price, profit])
                open_positions.remove(position)

        # BUY if price hits level and not already bought
        for level in grid_levels:
            if price <= level and not is_already_bought(level):
                open_positions.append({
                    'buy_price': level,
                    'amount': TRADE_AMOUNT_USDT,
                    'timestamp': now
                })
                trade_log.append([now, 'BUY', level, TRADE_AMOUNT_USDT])
                break

    # === Display Results ===
    df = pd.DataFrame(trade_log, columns=['Time', 'Action', 'Price', 'Amount/Profit'])
    st.subheader("📒 Trade Log")
    st.dataframe(df, use_container_width=True)

    st.subheader("💰 Profit Summary")
    st.metric("Total Simulated Profit", f"${total_profit:.2f}")

    st.subheader("📈 Price Chart")
    st.line_chart(df_prices['price'])
