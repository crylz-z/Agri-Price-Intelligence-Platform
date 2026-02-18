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
    Renders a sparkline area chart for the 7-day trend.
    Aggregates to daily average price before plotting.
    """
    if trend_df.empty:
        return

    st.markdown(f"**7-Day Price Trend ({category_name})**")

    # Aggregate to daily average — raw data has multiple markets per day
    daily_avg = (
        trend_df.groupby(trend_df["extract_dt"].dt.date)["Prevailing Price (₱)"]
        .mean()
        .reset_index()
    )
    daily_avg.columns = ["date", "avg_price"]
    daily_avg["date"] = pd.to_datetime(daily_avg["date"])

    if daily_avg.empty or len(daily_avg) < 2:
        st.caption("Insufficient data for trend chart.")
        return

    # Explicit domain — area charts fill to domain min, so set it close to data min
    y_min = float(daily_avg["avg_price"].min()) * 0.90
    y_max = float(daily_avg["avg_price"].max()) * 1.10

    chart = (
        alt.Chart(daily_avg)
        .mark_area(
            line={"color": "#2E86AB"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="white", offset=0),
                    alt.GradientStop(color="#2E86AB", offset=1),
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0,
            ),
            interpolate="monotone",
        )
        .encode(
            alt.X("date:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=0)),
            alt.Y(
                "avg_price:Q",
                title="Avg Price (₱)",
                scale=alt.Scale(domain=[y_min, y_max]),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("avg_price:Q", title="Avg Price", format="₱,.2f"),
            ],
        )
        .properties(height=180)
    )

    st.altair_chart(chart, use_container_width=True)



def render_gouging_alert(df, srp_df):
    """
    Scans for markets charging > 15% above SRP or Regional Average.
    Displays a Red Warning Box if found.
    """
    if df.empty:
        return

    # Prepare Data
    merged = df.copy()
    # If using SRP, we need to join. For simplification, let's look at relative outliers first
    # Or strict SRP check if SRP exists for commodity.

    # Let's perform a lightweight check against SRP if available
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

    # Diverging Scale: Blue (Cheap) -> White (Avg) -> Red (Expensive)
    # We clamp the domain visualization to -2 to +2 usually
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
