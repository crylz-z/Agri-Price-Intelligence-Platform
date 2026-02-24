import streamlit as st
import pandas as pd
import altair as alt


def render_kpi_cards(commodity_df, trend_df=None):
    """
    Renders the top row of KPI cards using COMPONENT-LEVEL data.
    1. Avg Price (Specific Commodity) + Delta
    2. Best Deal (Cheapest Market for this Commodity)
    3. Markets Reporting (Count)
    """
    if commodity_df.empty:
        st.warning("No data available for KPI calculation.")
        return

    # metrics
    avg_price = commodity_df["Prevailing Price (₱)"].mean()
    market_count = commodity_df["market_name"].nunique()

    # Calculate Delta (Day-Over-Day)
    price_delta = None
    if trend_df is not None and not trend_df.empty:
        # Get yesterday's average price
        # Assumes trend_df is sorted by date ascending
        dates = trend_df["extract_dt"].dt.date.unique()
        if len(dates) >= 2:
            yesterday_date = dates[-2]  # Second to last date
            # Filter for yesterday
            yesterday_df = trend_df[trend_df["extract_dt"].dt.date == yesterday_date]
            if not yesterday_df.empty:
                prev_avg = yesterday_df["Prevailing Price (₱)"].mean()
                if prev_avg > 0:
                    price_delta = f"{((avg_price - prev_avg) / prev_avg) * 100:.1f}%"

    # Best Deal Logic
    cheapest_row = commodity_df.loc[commodity_df["Prevailing Price (₱)"].idxmin()]
    cheapest_market = cheapest_row["market_name"]
    cheapest_price = cheapest_row["Prevailing Price (₱)"]
    full_comm_name = cheapest_row["commodity"]

    # Render
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.container(border=True):
            st.metric(
                "Avg Price",
                f"₱{avg_price:,.2f}",
                delta=price_delta,
                delta_color="inverse",
                help=f"Average prevailing price for {full_comm_name}",
            )

    with c2:
        with st.container(border=True):
            st.metric(
                "Best Deal",
                f"₱{cheapest_price:,.2f}",
                f"{cheapest_market}",
                help="Lowest price currently available",
            )

    with c3:
        with st.container(border=True):
            st.metric(
                "Markets Reporting",
                market_count,
                help=f"Number of markets reporting price for {full_comm_name}",
            )


def render_national_anomaly_detection(df):
    """
    Visualizes price outliers nationwide using a statistical distribution scatter.
    Markets with Z-Score > 1.5 are highlighted as 'Anomalies'.
    """
    if df.empty or "Prevailing Price (₱)" not in df.columns:
        return

    # 1. Statistical Calculations
    df = df.copy()
    df["price"] = pd.to_numeric(df["Prevailing Price (₱)"], errors="coerce")
    df = df.dropna(subset=["price"])

    mean_price = df["price"].mean()
    std_price = df["price"].std()

    if pd.isna(mean_price) or std_price == 0 or pd.isna(std_price):
        st.info("Pricing data is too uniform to detect national outliers.")
        return

    # Calculate Z-Scores
    df["z_score"] = (df["price"] - mean_price) / std_price
    df["is_anomaly"] = df["z_score"] > 1.5
    df = df.sort_values("price", ascending=False)

    # 2. Visualization
    # (Title handled by page markdown)

    # Base chart
    base = alt.Chart(df).encode(
        x=alt.X("market_name:N", sort="-y", title=None, axis=alt.Axis(labels=False)),
        y=alt.Y("price:Q", title="Price (₱)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("market_name:N", title="Market"),
            alt.Tooltip("region_name:N", title="Region"),
            alt.Tooltip("price:Q", title="Current Price", format=",.2f"),
            alt.Tooltip("z_score:Q", title="Z-Score", format=".2f"),
        ],
    )

    # National Average Rule
    rule = (
        alt.Chart(pd.DataFrame({"y": [mean_price]}))
        .mark_rule(color="#64748b", strokeDash=[4, 4], strokeWidth=2)
        .encode(y="y:Q")
    )

    # Points layer
    points = base.mark_circle(size=100).encode(
        color=alt.condition(
            alt.datum.z_score > 1.5,
            alt.value("#e11d48"),  # Coral Hike
            alt.value("#64748b"),  # Slate Neutral
        ),
        opacity=alt.condition(alt.datum.z_score > 1.5, alt.value(0.9), alt.value(0.5)),
    )

    chart = (points + rule).properties(height=380)
    st.altair_chart(chart, width="stretch")

    # Status Message
    anom_count = df[df["is_anomaly"]].shape[0]
    if anom_count > 0:
        st.error(
            f"**Disparity Detected**: {anom_count} markets are reporting prices significantly higher than the national statistical norm."
        )
    else:
        st.success("National pricing is currently within the statistical norm.")


def render_sparklines(trend_df, category_name, region_name):
    """
    Renders a 30-day price trend as a layered volatility band chart.
    """
    if trend_df is None or trend_df.empty:
        st.caption("No recent data found for trend analysis.")
        return

    st.markdown(f"**Price Trend (Last 30 Days) - {category_name} ({region_name})**")

    # 1. CLEAN & SANITIZE
    df = trend_df.copy()
    price_col = "Prevailing Price (\u20b1)"
    df["numeric_price"] = pd.to_numeric(df[price_col], errors="coerce")
    df = df.dropna(subset=["numeric_price"])

    if df.empty:
        st.caption("No valid price data reported in this window.")
        return

    # 2. AGGREGATE
    daily = (
        df.groupby(df["extract_dt"].dt.date)["numeric_price"]
        .agg(avg="mean", low="min", high="max")
        .reset_index()
    )
    daily.columns = ["date", "avg", "low", "high"]
    daily["date"] = pd.to_datetime(daily["date"])

    # 3. ENCODE
    x_enc = alt.X(
        "date:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30, tickCount=7)
    )
    y_scale = alt.Scale(zero=False)

    tooltips = [
        alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
        alt.Tooltip("avg:Q", title="Avg Price", format=",.2f"),
        alt.Tooltip("low:Q", title="Day Low", format=",.2f"),
        alt.Tooltip("high:Q", title="Day High", format=",.2f"),
    ]

    base = alt.Chart(daily).encode(x=x_enc)

    # Volatility Band
    band = base.mark_area(opacity=0.2, color="#475569", interpolate="monotone").encode(
        y=alt.Y("low:Q", title="Price (\u20b1)", scale=y_scale), y2=alt.Y2("high:Q")
    )

    # Average Line
    line = base.mark_line(
        point=alt.OverlayMarkDef(filled=True, size=60, color="#475569"),
        color="#475569",
        interpolate="monotone",
        strokeWidth=3,
    ).encode(
        y=alt.Y("avg:Q", title="Price (\u20b1)", scale=y_scale),
        tooltip=tooltips,
    )

    st.altair_chart((band + line).properties(height=180), width="stretch", theme=None)


def render_historical_baseline_delta(current_df, trend_df):
    """
    Calculates the % difference between today's price and the 30-day historical
    average for each market.
    """
    if current_df.empty or trend_df.empty:
        st.info("Insufficient historical context to calculate baseline delta.")
        return

    # 1. Calculate 30-day Baseline per Market
    baseline = (
        trend_df.groupby("market_name")["Prevailing Price (₱)"].mean().reset_index()
    )
    baseline.columns = ["market_name", "avg_30d"]

    # 2. Extract Current Prices
    current = current_df.copy()
    current["price_now"] = pd.to_numeric(
        current["Prevailing Price (₱)"], errors="coerce"
    )

    # 3. Join and Calculate Delta
    merged = pd.merge(
        current[["market_name", "price_now"]], baseline, on="market_name", how="inner"
    )

    if merged.empty:
        st.info("No matching market history found for baseline calculation.")
        return

    merged["pct_diff"] = (
        (merged["price_now"] - merged["avg_30d"]) / merged["avg_30d"]
    ) * 100
    merged = merged.sort_values("pct_diff", ascending=False)

    # 4. Visualize
    st.markdown("### Current Price vs 30-Day Market Average")
    st.caption(
        "Reading Guide: Compares today's price to the market's own 30-day historical average. Coral indicates a price hike; Teal indicates a price drop."
    )

    chart = (
        alt.Chart(merged)
        .mark_bar()
        .encode(
            y=alt.Y("market_name:N", sort=None, title=None),
            x=alt.X("pct_diff:Q", title="% Difference vs 30D Avg"),
            color=alt.condition(
                alt.datum.pct_diff > 0,
                alt.value("#e11d48"),  # Coral Hike
                alt.value("#0d9488"),  # Teal Drop
            ),
            tooltip=[
                alt.Tooltip("market_name:N", title="Market"),
                alt.Tooltip("avg_30d:Q", title="30-Day Avg", format=",.2f"),
                alt.Tooltip("price_now:Q", title="Current Price", format=",.2f"),
                alt.Tooltip("pct_diff:Q", title="% Difference", format=".1f"),
            ],
        )
        .properties(height=380)
    )

    st.altair_chart(chart, width="stretch", theme=None)


def render_category_substitutes(sub_df, selected_commodity):
    """
    Renders average pricing for alternative commodities within the same category.
    """
    if sub_df.empty:
        st.info("No regional substitutes found for this category.")
        return

    # Aggregate
    stats = sub_df.groupby("commodity")["Prevailing Price (₱)"].mean().reset_index()
    stats.columns = ["commodity", "price"]
    stats = stats.sort_values("price", ascending=True)

    st.markdown("### Regional Category Substitutes")
    st.caption(
        "Reading Guide: Average pricing of alternative commodities within the same category for this region."
    )

    chart = (
        alt.Chart(stats)
        .mark_bar()
        .encode(
            y=alt.Y("commodity:N", sort=None, title=None),
            x=alt.X("price:Q", title="Avg Price (₱)"),
            color=alt.condition(
                alt.datum.commodity == selected_commodity,
                alt.value("#0d9488"),  # Teal (Current Selection)
                alt.value("#64748b"),  # Slate (Substitutes)
            ),
            tooltip=[
                alt.Tooltip("commodity:N", title="Commodity"),
                alt.Tooltip("price:Q", title="Avg Price", format=",.2f"),
            ],
        )
        .properties(height=380)
    )

    st.altair_chart(chart, width="stretch", theme=None)


def render_national_insight(truth_df, commodity: str) -> None:
    """
    Renders a macro-level insight banner focusing on regional spread.
    Identifies the cheapest and most expensive regions for a commodity.
    """
    if truth_df.empty:
        return

    # Aggregate by Region
    reg_stats = (
        truth_df.groupby("region_name")["Prevailing Price (₱)"].mean().reset_index()
    )
    reg_stats.columns = ["region", "avg_price"]

    if reg_stats.empty:
        return

    cheapest = reg_stats.loc[reg_stats["avg_price"].idxmin()]
    expensive = reg_stats.loc[reg_stats["avg_price"].idxmax()]

    national_avg = reg_stats["avg_price"].mean()
    disparity = (
        (expensive["avg_price"] - cheapest["avg_price"]) / cheapest["avg_price"]
    ) * 100

    insight_text = (
        f"**Macro Insight:** {commodity} averages **₱{national_avg:,.2f}** nationwide. "
        f"The most affordable region is **{cheapest['region']}** (₱{cheapest['avg_price']:,.2f}), "
        f"while **{expensive['region']}** reports the highest average (₱{expensive['avg_price']:,.2f}). "
        f"There is a **{disparity:.1f}% price disparity** between these extremes today."
    )

    st.info(insight_text)


def render_zscore_chart(df, height=400):
    """
    Renders a bar chart showing the Z-Score (Price Fairness) for each market.
    Z > 0: Expensive
    Z < 0: Cheap
    Sorted by Z-Score ascending (Cheapest first).
    """
    if df.empty:
        return

    # Calculate Z-Score
    mean = df["Prevailing Price (₱)"].mean()
    std = df["Prevailing Price (₱)"].std()

    if std == 0:
        return  # No variation

    df = df.copy()
    df["z_score"] = (df["Prevailing Price (₱)"] - mean) / std

    # Sort data explicitly
    df = df.sort_values("z_score", ascending=True)

    # Title handled in page layout

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("z_score:Q", title="Z-Score (Deviation from Average)"),
            y=alt.Y("market_name:N", sort=None, title=None),
            color=alt.Color(
                "z_score:Q",
                scale=alt.Scale(
                    domain=[-2, 0, 2],
                    range=["#0d9488", "#64748b", "#e11d48"],  # Teal, Slate, Coral
                ),
                legend=None,
            ),
            tooltip=["market_name", "Prevailing Price (₱)", "z_score"],
        )
        .properties(height=380)
        .interactive()
    )

    st.altair_chart(chart, width="stretch", theme=None)


def render_regional_insight(trend_df, commodity: str, truth_df=None) -> None:
    """
    Renders a strategic snapshot of regional price performance.
    """
    if trend_df is None or trend_df.empty:
        st.warning(f"Technical: Insufficient historical baseline for {commodity}.")
        return

    avg_30d = trend_df["Prevailing Price (₱)"].mean()
    latest_date = trend_df["extract_dt"].max()
    current_trend_df = trend_df[trend_df["extract_dt"] == latest_date]
    current_avg = current_trend_df["Prevailing Price (₱)"].mean()

    best_source = (
        truth_df if truth_df is not None and not truth_df.empty else current_trend_df
    )

    if pd.isna(avg_30d) or pd.isna(current_avg) or avg_30d == 0 or best_source.empty:
        st.warning(
            f"Data Analysis: Sparse telemetry prevents insight generation for {commodity}."
        )
        return

    pct_diff = ((current_avg - avg_30d) / avg_30d) * 100
    direction = "below" if pct_diff < 0 else "above"
    abs_pct = abs(pct_diff)

    best_market_row = best_source.loc[best_source["Prevailing Price (₱)"].idxmin()]
    best_market = best_market_row["market_name"]
    best_price = best_market_row["Prevailing Price (₱)"]

    status_prefix = "Optimal" if pct_diff < 0 else "Monitoring"
    insight_text = (
        f"**{status_prefix} Status:** {commodity} pricing is currently **{abs_pct:.1f}% {direction}** "
        f"the 30-day baseline (₱{avg_30d:,.2f}). "
        f"Market Leader: **{best_market}** at ₱{best_price:,.2f}."
    )

    if pct_diff < 0:
        st.success(insight_text)
    else:
        st.info(insight_text)


def render_historical_period_insight(df, commodity: str) -> None:
    """
    Renders strategic temporal analytics for the selected timeframe.
    """
    required_cols = {"extract_dt", "Prevailing Price (₱)"}
    if df is None or df.empty or not required_cols.issubset(df.columns):
        st.warning(
            f"Technical Error: Dataset incomplete for {commodity} temporal analysis."
        )
        return

    # Calculate volatility (std dev / mean)
    mean_p = df["Prevailing Price (₱)"].mean()
    std_p = df["Prevailing Price (₱)"].std()
    volatility = (std_p / mean_p) * 100 if mean_p > 0 else 0

    dow_df = df.copy()
    dow_df["day_name"] = dow_df["extract_dt"].dt.day_name()
    dow_avg = dow_df.groupby("day_name")["Prevailing Price (₱)"].mean()

    if dow_avg.empty:
        st.warning(f"Data Gaps: Insufficient day-of-week telemetry for {commodity}.")
        return

    best_day = dow_avg.idxmin()
    best_price = dow_avg.min()

    insight_text = (
        f"**Temporal Analysis:** {commodity} exhibits a **{volatility:.1f}% volatility index** over this period. "
        f"Strategic analysis identifies **{best_day}** as the optimal procurement window (Average: ₱{best_price:,.2f})."
    )

    st.success(insight_text)


def render_market_leaderboard(df, commodity: str):
    """
    Renders a horizontal bar chart ranking markets by price.
    Cheapest market ALWAYS at the top.
    """
    if df is None or df.empty:
        st.info("No market data available for the leaderboard.")
        return

    # Data Prep
    df = df.copy()
    df["price"] = pd.to_numeric(df["Prevailing Price (₱)"], errors="coerce").astype(
        float
    )
    df["market"] = df["market_name"].astype(str)

    # Pre-format labels manually to avoid Altair format bugs
    df["label"] = df["price"].apply(lambda x: f"₱{x:,.2f}" if pd.notnull(x) else "N/A")

    # Sort Ascending (Cheapest first)
    df = df.sort_values("price", ascending=True)

    # 80/20 color rule (Min=Teal, Max=Coral, Mid=Slate)
    min_p = df["price"].min()
    max_p = df["price"].max()

    def get_color(p):
        if p == min_p:
            return "#0d9488"  # Teal
        if p == max_p:
            return "#e11d48"  # Coral
        return "#64748b"  # Slate

    df["color"] = df["price"].apply(get_color)

    st.markdown(f"**Market Price Rankings: {commodity}**")

    base = alt.Chart(df).encode(
        y=alt.Y("market:N", sort=None, title=None),
        x=alt.X("price:Q", title="Price (₱)"),
        color=alt.Color("color:N", scale=None),  # Use the hex codes directly
    )

    bars = base.mark_bar()

    # Add text labels with high contrast
    text = base.mark_text(
        align="left", baseline="middle", dx=5, color="#1e293b"
    ).encode(text=alt.Text("label:N"))

    chart = (
        (bars + text)
        .properties(height=max(300, len(df) * 35))
        .configure_axis(labelFontSize=10, titlePadding=15)
    )

    st.altair_chart(chart, width="stretch", theme=None)
