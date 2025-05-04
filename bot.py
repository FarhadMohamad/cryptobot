import pandas as pd
import datetime
from binance.client import Client
import streamlit as st

# === Load API credentials from Streamlit Secrets ===
API_KEY = st.secrets["BINANCE_API_KEY"]
API_SECRET = st.secrets["BINANCE_API_SECRET"]

# === Streamlit UI ===
st.set_page_config(page_title="Grid Trading Bot", layout="wide")
st.title("📈 DOGEUSDT Grid Trading Backtest")
st.write("Simulate a grid trading strategy using real Binance data.")

# === Layout: All inputs on left except start/end dates on right ===
left, right = st.columns([2, 1])

with left:
    SYMBOL = st.text_input("Trading Pair (e.g., DOGEUSDT)", "DOGEUSDT", help="The symbol of the crypto pair you want to simulate, like DOGEUSDT or BTCUSDT.")
    LOWER_BOUND = st.number_input("Lower Bound Price", value=0.16, step=0.001, help="The lowest price to place a grid order.")
    UPPER_BOUND = st.number_input("Upper Bound Price", value=0.18, step=0.001, help="The highest price to place a grid order.")
    GRID_SPACING = st.number_input("Grid Spacing ($)", value=0.002, step=0.0001, help="Distance between each grid level. Should be greater than 0.")
    TRADE_AMOUNT_USDT = st.number_input("Amount per Trade ($)", value=100, step=10, help="The amount of USDT to use per grid order.")

with right:
    start_date = st.date_input("Start Date", datetime.date(2025, 3, 1), help="The date to start the simulation from.")
    end_date = st.date_input("End Date", datetime.date(2025, 6, 1), help="The date to end the simulation.")

# === Run Button ===
run_bot = st.button("Run Simulation")

if run_bot and API_KEY and API_SECRET:
    if GRID_SPACING <= 0:
        st.error("Grid Spacing must be greater than 0.")
    else:
        # === Initialize Binance Client with test ===
        try:
            client = Client(API_KEY, API_SECRET)
            client.ping()  # Test connection to Binance
            st.success("✅ Successfully connected to Binance API.")
        except Exception as e:
            st.error(f"❌ Failed to connect to Binance API: {e}")
            st.stop()

        # === Fetch historical data ===
        st.write("Fetching historical data from Binance API...")
        klines = client.get_historical_klines(SYMBOL, Client.KLINE_INTERVAL_1HOUR, str(start_date), str(end_date))

        # Convert to DataFrame
        df_all = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        df_all['datetime'] = pd.to_datetime(df_all['Open time'], unit='ms')
        df_all.set_index('datetime', inplace=True)
        df_all['price'] = df_all['Close'].astype(float)
        df_prices = df_all[['price']]

        # === Generate Grid Levels ===
        grid_levels = []
        level = LOWER_BOUND
        while level <= UPPER_BOUND:
            grid_levels.append(round(level, 4))
            level += GRID_SPACING

        # === Run Grid Trading Simulation ===
        open_positions = []
        trade_log = []
        total_profit = 0

        def is_already_bought(level):
            return any(pos['buy_price'] == level for pos in open_positions)

        for time, price in df_prices['price'].items():
            now = time

            # SELL simulation
            for position in open_positions[:]:
                sell_price = position['buy_price'] + GRID_SPACING
                if price >= sell_price:
                    profit = GRID_SPACING * TRADE_AMOUNT_USDT / position['buy_price']
                    total_profit += profit
                    trade_log.append([now, 'SELL', sell_price, profit])
                    open_positions.remove(position)

            # BUY simulation
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
        st.subheader("💹 Trade Log")
        st.dataframe(df, use_container_width=True)

        st.subheader("📊 Profit Summary")
        st.metric(label="Total Simulated Profit", value=f"${total_profit:.2f}")

        st.line_chart(df_prices['price'])

elif run_bot:
    st.error("Missing Binance API Key or Secret in your Streamlit secrets configuration.")