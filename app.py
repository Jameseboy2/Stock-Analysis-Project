import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Stock Analyzer", layout="wide")

# -----------------------------------------------------------------------------
# USER INPUTS
# -----------------------------------------------------------------------------
st.sidebar.header("Search & Date Controls")
ticker = st.sidebar.text_input("1. Search Stocks (e.g., AAPL, TSLA)", "AAPL").upper()
start_date = st.sidebar.date_input("2. Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("3. End Date", pd.to_datetime("today"))

st.sidebar.markdown("---")
st.sidebar.subheader("Analysis Parameters")
growth_threshold = st.sidebar.slider(
    "High-Growth Threshold (%)", 
    min_value=0.0, 
    max_value=15.0, 
    value=2.0, 
    step=0.5,
    help="Filter days where the stock price jumped by at least this percentage."
)

# -----------------------------------------------------------------------------
# DATA LOADING & ALGORITHM ENGINE
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(symbol, start, end):
    # Download price data
    df = yf.download(symbol, start=start, end=end)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df['Daily_Return_Pct'] = ((df['Close'] - df['Open']) / df['Open']) * 100
    df['Year'] = df.index.year
    
    # RSI Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Fetch the actual company name
    ticker_obj = yf.Ticker(symbol)
    company_name = ticker_obj.info.get('shortName', symbol)
    
    return df, company_name

try:
    df, company_name = load_data(ticker, start_date, end_date)
    st.title(f"Analysis Dashboard: {company_name}")
except Exception as e:
    st.error(f"Error loading data. Please ensure '{ticker}' is a valid symbol.")
    st.stop()

# -----------------------------------------------------------------------------
# LIVE METRICS & BUY/SELL SIGNAL
# -----------------------------------------------------------------------------
latest_price = df['Close'].iloc[-1]
previous_price = df['Close'].iloc[-2]
price_change = latest_price - previous_price
latest_rsi = df['RSI'].iloc[-1]

# Prediction Logic
if latest_rsi < 30:
    signal = "BUY (Oversold)"
elif latest_rsi > 70:
    signal = "SELL (Overbought)"
else:
    signal = "HOLD (Neutral)"

colA, colB, colC = st.columns(3)
colA.metric("Current Price", f"${latest_price:.2f}", f"${price_change:.2f}")
colB.metric("Current RSI (14-Day)", f"{latest_rsi:.1f}")
colC.metric("Algorithm Suggestion", signal)

st.markdown("---")

# -----------------------------------------------------------------------------
# VISUALIZATION (With Chart Toggle)
# -----------------------------------------------------------------------------
# Let the user toggle the chart type
chart_type = st.radio("Select Chart Type:", ["Line Graph", "Candlestick"], horizontal=True)

fig = go.Figure()

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name="Price"))
else:
    # Use go.Scatter to draw a simple line based on the Close price
    fig.add_trace(go.Scatter(x=df.index, 
                             y=df['Close'], 
                             mode='lines', 
                             name='Close Price',
                             line=dict(color='#1f77b4', width=2)))

fig.update_layout(title=f"{company_name} Price Action", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# ANALYTICAL QUESTIONS (Filter, Sort, Aggregate)
# -----------------------------------------------------------------------------
st.subheader("Deep Dive Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### Top High-Growth Days (> {growth_threshold}%)")
    st.write("Identifies the best intra-day performance based on your slider.")
    
    high_growth_days = df[df['Daily_Return_Pct'] >= growth_threshold]
    sorted_growth = high_growth_days.sort_values(by='Daily_Return_Pct', ascending=False)
    
    if sorted_growth.empty:
        st.info("No days found matching this threshold. Try lowering the slider.")
    else:
        st.dataframe(sorted_growth[['Open', 'Close', 'Daily_Return_Pct', 'Volume']].head(5))

with col2:
    st.markdown("### Average Daily Volume by Year")
    st.write("Aggregates trading volume to spot liquidity trends.")
    
    volume_analysis = df.groupby('Year')['Volume'].mean().reset_index()
    volume_analysis['Volume'] = volume_analysis['Volume'].map('{:,.0f}'.format)
    
    st.table(volume_analysis)