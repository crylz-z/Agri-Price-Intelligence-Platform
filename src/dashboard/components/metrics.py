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


def render_sparklines(trend_df, category_name):
    """
    Renders a 30-day price trend as a layered volatility band chart.

    Layer 1 (bottom): semi-transparent mark_area between the day's min and max
    price — the volatility band. Width of the band reveals intra-day spread.

    Layer 2 (top): solid mark_line(point=True) showing the daily average.
    A dot appears only on days where data was collected, exposing pipeline gaps.

    Expects trend_df with columns: 'extract_dt', 'Prevailing Price (₱)'.
    """
    if trend_df.empty:
        st.caption("No recent data found for trend analysis.")
        return

    st.markdown(f"**Price Trend (Last 30 Days) - {category_name}**")

    # Aggregate to daily statistics: avg, min, max.
    grp = trend_df.groupby(trend_df["extract_dt"].dt.date)["Prevailing Price (₱)"]
    daily = grp.agg(avg_price="mean", min_price="min", max_price="max").reset_index()
    daily.columns = ["date", "avg_price", "min_price", "max_price"]
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.dropna()

    if daily.empty:
        st.caption("No data available for trend chart.")
        return

    # Shared encodings.
    x_enc = alt.X(
        "date:T",
        title=None,
        axis=alt.Axis(format="%b %d", labelAngle=-30, tickCount=7),
    )
    y_scale = alt.Scale(zero=False)

    # Tooltips shown on the line/point layer.
    tooltips = [
        alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
        alt.Tooltip("avg_price:Q", title="Avg Price (₱)", format=",.2f"),
        alt.Tooltip("min_price:Q", title="Day Low (₱)", format=",.2f"),
        alt.Tooltip("max_price:Q", title="Day High (₱)", format=",.2f"),
    ]

    base = alt.Chart(daily).encode(x=x_enc)

    if len(daily) == 1:
        # Single data point: render as a labelled dot.
        point = base.mark_point(filled=True, size=120, color="#2E86AB").encode(
            y=alt.Y("avg_price:Q", title="Avg Price (₱)", scale=y_scale),
            tooltip=tooltips,
        )
        label = base.mark_text(dy=-15, color="#2E86AB").encode(
            y=alt.Y("avg_price:Q", scale=y_scale),
            text=alt.Text("avg_price:Q", format=",.2f"),
        )
        chart = point + label
    else:
        # Layer 1: volatility band (min → max per day), semi-transparent.
        band = base.mark_area(opacity=0.2, color="#2E86AB", interpolate="monotone").encode(
            y=alt.Y("min_price:Q", title="Price (₱)", scale=y_scale),
            y2=alt.Y2("max_price:Q"),
        )

        # Layer 2: daily average line with point markers.
        line = base.mark_line(
            point=alt.OverlayMarkDef(filled=True, size=60, color="#2E86AB"),
            color="#2E86AB",
            interpolate="monotone",
            strokeWidth=2,
        ).encode(
            y=alt.Y("avg_price:Q", title="Price (₱)", scale=y_scale),
            tooltip=tooltips,
        )

        chart = band + line

    st.altair_chart(chart.properties(height=180), use_container_width=True)


def render_gouging_alert(df, srp_df):
    """
    Scans for markets charging > 15% above SRP or Regional Average.
    Displays a Red Warning Box if found.
    """
    if df.empty:
        return

    alerts = []

    # Group by commodity to check
    for commodity in df["commodity"].unique():
        subset = df[df["commodity"] == commodity]
        srp_row = srp_df[srp_df["commodity"] == commodity]

        if not srp_row.empty:
            srp = srp_row.iloc[0]["srp"]
            threshold = srp * 1.15  # 15% buffer

            # Find violators
            violators = subset[subset["Prevailing Price (₱)"] > threshold]
            for _, row in violators.iterrows():
                diff_pct = ((row["Prevailing Price (₱)"] - srp) / srp) * 100
                alerts.append(
                    f"**{row['market_name']}**: {commodity} @ ₱{row['Prevailing Price (₱)']:.2f} (+{diff_pct:.0f}% vs SRP)"
                )

    if alerts:
        with st.expander(
            f"PRICE GOUGING DETECTED ({len(alerts)} Markets)", expanded=True
        ):
            st.error(
                "The following markets are charging >15% above the Suggested Retail Price:"
            )
            for a in alerts[:5]:  # Show top 5 to avoid flooding
                st.markdown(f"- {a}")
            if len(alerts) > 5:
                st.caption(f"...and {len(alerts)-5} more.")
    else:
        st.success("No Price Gouging Detected (All markets within 15% of SRP).")


def render_zscore_chart(df, height=400):
    """
    Renders a bar chart showing the Z-Score (Price Fairness) for each market.
    Z > 0: Expensive (Red)
    Z < 0: Cheap (Green)
    Uses a Diverging Color Scale for subtlety.
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

    st.markdown("**Price Fairness Index (Green = Cheaper, Red = More Expensive)**")

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("z_score:Q", title="Z-Score (Deviation from Average)"),
            y=alt.Y("market_name:N", sort="-x", title=None),
            color=alt.Color(
                "z_score:Q",
                scale=alt.Scale(scheme="redyellowgreen", domain=[2, -2]),
                legend=None,
            ),
            tooltip=["market_name", "Prevailing Price (₱)", "z_score"],
        )
        .properties(height=height)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


def render_national_insight(df, commodity: str) -> None:
    """
    Renders a snapshot-focused insight banner for the National Market Watch page.
    Compares the current day's price against the 30-day average and names the
    single cheapest market available today.

    Parameters
    ----------
    df : pd.DataFrame
        Historical trend DataFrame with columns: 'extract_dt',
        'Prevailing Price (₱)', 'market_name'.
    commodity : str
        Human-readable commodity name.
    """
    required_cols = {"extract_dt", "Prevailing Price (₱)", "market_name"}
    if df is None or df.empty or not required_cols.issubset(df.columns):
        st.warning(f"Insufficient data to generate an insight for {commodity}.")
        return

    avg_30d = df["Prevailing Price (₱)"].mean()
    latest_date = df["extract_dt"].max()
    current_df = df[df["extract_dt"] == latest_date]
    current_price = current_df["Prevailing Price (₱)"].mean()

    if pd.isna(avg_30d) or pd.isna(current_price) or avg_30d == 0:
        st.warning(f"Insufficient data to generate an insight for {commodity}.")
        return

    pct_diff = ((current_price - avg_30d) / avg_30d) * 100
    direction = "cheaper" if pct_diff < 0 else "more expensive"
    abs_pct = abs(pct_diff)

    best_market_row = current_df.loc[current_df["Prevailing Price (₱)"].idxmin()]
    best_market = best_market_row["market_name"]
    best_price = best_market_row["Prevailing Price (₱)"]

    insight_text = (
        f"**Insight:** {commodity} is currently **{abs_pct:.1f}% {direction}** "
        f"than the 30-day average (₱{avg_30d:,.2f}). "
        f"The absolute best deal today is at **{best_market}** at ₱{best_price:,.2f}."
    )

    if pct_diff < 0:
        st.success(insight_text)
    else:
        st.info(insight_text)


def render_historical_insight(df, commodity: str) -> None:
    """
    Renders a long-term volatility insight banner for the Historical Trends page.
    Reports the price spread over the full period and identifies the statistically
    cheapest day of the week to buy based on historical averages.

    Parameters
    ----------
    df : pd.DataFrame
        Historical trend DataFrame with columns: 'extract_dt',
        'Prevailing Price (₱)'.
    commodity : str
        Human-readable commodity name.
    """
    required_cols = {"extract_dt", "Prevailing Price (₱)"}
    if df is None or df.empty or not required_cols.issubset(df.columns):
        st.warning(f"Insufficient data to generate a historical insight for {commodity}.")
        return

    price_spread = df["Prevailing Price (₱)"].max() - df["Prevailing Price (₱)"].min()

    # Day-of-week analysis: find the cheapest day on average.
    dow_df = df.copy()
    dow_df["day_name"] = dow_df["extract_dt"].dt.day_name()
    dow_avg = dow_df.groupby("day_name")["Prevailing Price (₱)"].mean()

    if dow_avg.empty:
        st.warning(f"Insufficient data to generate a historical insight for {commodity}.")
        return

    best_day = dow_avg.idxmin()

    insight_text = (
        f"**Insight:** Over the selected period, **{commodity}** prices have fluctuated "
        f"by **₱{price_spread:,.2f}**. "
        f"Historical data suggests **{best_day}** is statistically the best day of the week to buy."
    )

    st.info(insight_text)
