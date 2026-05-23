import pandas as pd
import yfinance as yf
import streamlit as st
from ta.momentum import RSIIndicator
import mplfinance as mpf
import matplotlib.pyplot as plt
import json
import time

# =====================================
# タイトル
# =====================================

st.set_page_config(
    page_title="AI株投資 かげやまくん",
    page_icon="🐻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""

<style>

.main {
    background:
    linear-gradient(
        135deg,
        #0E1117 0%,
        #151922 100%
    );
}

/* KPIカード */

.glass-card {

    background: rgba(
        26,
        29,
        36,
        0.7
    );

    backdrop-filter: blur(12px);

    border: 1px solid rgba(
        255,
        255,
        255,
        0.08
    );

    border-radius: 20px;

    padding: 24px;

    box-shadow:
        0 8px 32px rgba(
            0,
            255,
            170,
            0.08
        );

    transition: 0.3s;
}

.glass-card:hover {

    transform: translateY(-4px);

    box-shadow:
        0 12px 40px rgba(
            0,
            255,
            170,
            0.18
        );
}

</style>

""", unsafe_allow_html=True)

# =====================================
# テーマ選択
# =====================================

with open(
    "data/themes.json",
    "r",
    encoding="utf-8"
) as f:

    theme_data = json.load(f)

theme_options = list(
    theme_data.keys()
)

theme_counts = {}

for theme_name, stocks in theme_data.items():

    theme_counts[theme_name] = len(
        stocks
    )

st.sidebar.markdown(
    "## 🔥 テーマランキング"
)

for theme_name, count in sorted(

    theme_counts.items(),

    key=lambda x: x[1],

    reverse=True
):

    st.sidebar.markdown(
        f"### {theme_name} ({count})"
    )

theme = st.selectbox(
    "テーマを選択",
    theme_options
)

st.sidebar.header("⚙️ スクリーニング条件")

rsi_threshold = st.sidebar.slider(
    "RSI上限",
    30,
    70,
    50
)

divergence_min = st.sidebar.slider(
    "乖離率 最小",
    -15,
    0,
    -10
)

divergence_max = st.sidebar.slider(
    "乖離率 最大",
    -15,
    5,
    -3
)

growth_threshold = st.sidebar.slider(
    "最低売上成長率",
    -20,
    100,
    0
)

per_threshold = st.sidebar.slider(
    "PER上限",
    0,
    100,
    40
)

# =====================================
# テーマ自動生成
# =====================================

@st.cache_data(ttl=86400)
def get_theme_stocks(theme):

    with open(
        "data/themes.json",
        "r",
        encoding="utf-8"
    ) as f:

        theme_data = json.load(f)

    data = theme_data.get(
        theme,
        []
    )

    return pd.DataFrame(data)


@st.cache_data(ttl=3600)
def get_stock_data(ticker):

    stock = yf.Ticker(ticker)

    info = stock.info

    # =====================================
    # PER / PBR
    # =====================================

    per = info.get("trailingPE")
    pbr = info.get("priceToBook")

    # =====================================
    # 売上成長率
    # =====================================

    financials = stock.financials

    revenue_growth = None

    if (
        "Total Revenue" in financials.index
        and len(financials.columns) >= 2
    ):

        latest_revenue = financials.loc["Total Revenue"].iloc[0]
        previous_revenue = financials.loc["Total Revenue"].iloc[1]

        revenue_growth = (
            (latest_revenue - previous_revenue)
            / previous_revenue
        ) * 100

    # =====================================
    # 株価履歴
    # =====================================

    hist = stock.history(period="6mo")

    rsi = None
    divergence = None
    signal = "なし"

    if not hist.empty:

        # RSI
        rsi_indicator = RSIIndicator(close=hist["Close"])

        rsi = rsi_indicator.rsi().iloc[-1]

        # 25日線
        hist["MA25"] = (
            hist["Close"]
            .rolling(window=25)
            .mean()
        )

        current_price = hist["Close"].iloc[-1]
        ma25 = hist["MA25"].iloc[-1]

        divergence = (
            (current_price - ma25)
            / ma25
        ) * 100

    return {
        "PER": per,
        "PBR": pbr,
        "売上成長率(%)": revenue_growth,
        "RSI": rsi,
        "25日線乖離率(%)": divergence
    }

@st.cache_data(ttl=3600)
def get_chart_data(ticker, period):

    stock = yf.Ticker(ticker)

    hist = stock.history(period=period)

    hist["MA25"] = (
        hist["Close"]
        .rolling(window=25)
        .mean()
    )

    return hist

# =====================================
# テーマ自動生成
# =====================================

stock_list = get_theme_stocks(
    theme
)

if stock_list.empty:

    st.warning(
        "⚠️ テーマ銘柄が見つかりません"
    )

    st.stop()

# =====================================
# 実行ボタン
# =====================================

if st.button("スクリーニング開始"):
    st.session_state["run_screening"] = True

if st.session_state.get("run_screening"):

    data = []

    progress = st.progress(0)

    status_text = st.empty()

    for idx, (_, row) in enumerate(stock_list.iterrows()):

        name = row["name"]
        ticker = row["ticker"]

        try:
            result = get_stock_data(ticker)

            per = result["PER"]
            pbr = result["PBR"]
            revenue_growth = result["売上成長率(%)"]
            rsi = result["RSI"]
            divergence = result["25日線乖離率(%)"]

            signal = "なし"
            comment = ""

            if (
                rsi is not None
                and divergence is not None
                and revenue_growth is not None
                and per is not None
            ):

                if (
                    rsi is not None
                    and divergence is not None
                ):

                    if rsi < 40:
                        signal = "🟢 押し目候補"

                    elif rsi > 70:
                        signal = "🔥 過熱"

                    else:
                        signal = "⚪ 中立"

                    # =====================================
                    # AIコメント
                    # =====================================

                    if revenue_growth is not None:

                        if revenue_growth > 20:
                            comment += "🚀 高成長を維持。 "

                        elif revenue_growth < 0:
                            comment += "📉 売上成長が鈍化。 "

                    if rsi is not None:

                        if rsi < 40:
                            comment += "🟢 RSI低下で押し目水準。 "

                        elif rsi > 70:
                            comment += "🔥 過熱感に注意。 "

                    if divergence is not None:

                        if divergence < -5:
                            comment += "📉 移動平均線から大きく下落。 "

                    if per is not None:

                        if per < 15:
                            comment += "💰 PER割安感あり。 "

                        elif per > 40:
                            comment += "⚠️ PER高水準。 "

            # =====================================
            # データ追加
            # =====================================

            data.append({
                "銘柄": name,
                "PER": per,
                "PBR": pbr,
                "売上成長率(%)": revenue_growth,
                "RSI": rsi,
                "25日線乖離率(%)": divergence,
                "判定": signal,
                "AI分析": comment
            })

        except Exception as e:

            st.warning(f"{name} エラー: {e}")

        # ローディング演出
        status_text.markdown(f"""
        <div style='padding:10px;
        background-color:#1A1D24;
        border-radius:10px;
        margin-bottom:10px;'>

        <p style='color:#00FFAA;
        font-size:18px;'>

        🤖 AI分析中...
        <br>
        📡 {name} をスキャンしています

        </p>

        </div>
        """, unsafe_allow_html=True)

        # プログレスバー更新
        progress.progress(
            (idx + 1) / len(stock_list)
        )

    status_text.success(
        "✅ 分析完了！"
    )

    time.sleep(1)

    status_text.empty()

    progress.empty()

    # =====================================
    # DataFrame化
    # =====================================

    df = pd.DataFrame(data)

    if not df.empty:

        df = df.dropna(subset=["PER"])

    else:

        st.warning("⚠️ データ取得に失敗しました")
        st.stop()

    numeric_cols = [
        "PER",
        "PBR",
        "売上成長率(%)",
        "RSI",
        "25日線乖離率(%)"
    ]

    for col in numeric_cols:
        df[col] = df[col].round(2)

    # =====================================
    # スコア
    # =====================================

    df["スコア"] = (
        df["売上成長率(%)"] * 2
        - df["PER"]
        - (df["RSI"] * 0.3)
    )

    # =====================================
    # 判定ボーナス
    # =====================================

    df.loc[
        df["判定"] == "🟢 押し目候補",
        "スコア"
    ] += 30

    df.loc[
        df["判定"] == "🔥 過熱",
        "スコア"
    ] -= 30

    df = df.sort_values(
        by="スコア",
        ascending=False
    )

    # 順位追加
    df.insert(0, "順位", range(1, len(df) + 1))

    push_df = df

    tab1, tab2 = st.tabs([
    "📊 ランキング",
    "📈 チャート"
    ])

    # =====================================
    # 表示
    # =====================================

    with tab1:
        top_stock = df.iloc[0]

        # =====================================
        # TOP3カード
        # =====================================

        top3 = df.head(3)

        cols = st.columns(
            [1,1,1],
            gap="small"
        )

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        for idx, (_, row) in enumerate(
            top3.iterrows()
        ):

            with cols[idx]:

                st.markdown(f"""

                <div class='glass-card'>

                <h2 style='color:#00FFAA;'>

                {medals[idx]} #{idx+1}

                </h2>

                <h2 style='color:white;'>

                {row['銘柄']}

                </h2>

                <p style='color:#BBBBBB;
                min-height:45px;
                font-size:14px;'>

                {row['AI分析']}

                </p>

                <hr style='border:1px solid #333;'>

                <p style='color:white;
                font-size:16px;'>

                📉 RSI:
                {row['RSI']}

                <br>

                💰 PER:
                {row['PER']}

                <br>

                🎯 判定:
                {row['判定']}

                </p>

                </div>

                """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style='padding:16px;
        background-color:#1A1D24;
        border-radius:15px;
        margin-bottom:20px;
        border:1px solid #00FFAA;'>

        <h2 style='color:#00FFAA;'>
        🏆 今日の注目銘柄
        </h2>

        <h1 style='color:white;'>
        {top_stock['銘柄']}
        </h1>

        <p style='color:#BBBBBB; font-size:18px;'>
        {top_stock['AI分析']}
        </p>

        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        kpi_data = [

            (
                "📊 押し目候補数",
                len(df),
                "#00FFAA"
            ),

            (
                "📉 平均RSI",
                round(df["RSI"].mean(), 1),
                "#4DA3FF"
            ),

            (
                "💰 平均PER",
                round(df["PER"].mean(), 1),
                "#FFB84D"
            )
        ]

        for col, (title, value, color) in zip(
            [col1, col2, col3],
            kpi_data
        ):

            with col:

                st.markdown(f"""

                <div class='glass-card'
                style='text-align:center;'>

                <h3 style='color:{color};
                margin-bottom:10px;'>

                {title}

                </h3>

                <h1 style='color:white;
                font-size:32px;'>

                {value}

                </h1>

                </div>

                """, unsafe_allow_html=True)

        # st.subheader(
        # f"📊 {theme} 押し目ランキング"
        # )

        def color_signal(val):

            if "押し目" in str(val):
                return (
                    "background-color: #123524;"
                    "color: #00FFAA;"
                )

            elif "過熱" in str(val):
                return (
                    "background-color: #3A1A1A;"
                    "color: #FF4B4B;"
                )

            return ""

        # styled_df = (
        #     push_df.style
        #     .map(
        #         color_signal,
        #         subset=["判定"]
        #     )
        #     .background_gradient(
        #         subset=["RSI"],
        #         cmap="RdYlGn_r"
        #     )
        #     .background_gradient(
        #         subset=["売上成長率(%)"],
        #         cmap="Greens"
        #     )
        #     .background_gradient(
        #         subset=["PER"],
        #         cmap="Reds_r"
        #     )
        # )

        # st.dataframe(
        #     styled_df,
        #     use_container_width=True,
        #     height=700,
        #     column_config={
        #         "AI分析": st.column_config.TextColumn(
        #             width="large"
        #         )
        #     }
        # )

        st.markdown(
            f"## 📊 {theme} 押し目ランキング"
        )

        for _, row in push_df.iterrows():

            signal_color = "#00FFAA"

            if "過熱" in str(row["判定"]):

                signal_color = "#FF4B4B"

            st.markdown(f"""

            <div class='glass-card'
            style='margin-bottom:12px;
            padding:16px;'>

            <div style='display:flex;
            justify-content:space-between;
            align-items:flex-start;'>

            <div style='width:70%;'>

            <h3 style='color:white;
            margin-bottom:6px;'>

            #{row['順位']}
            {row['銘柄']}

            </h3>

            <p style='color:#BBBBBB;
            font-size:13px;
            margin-bottom:0;'>

            {row['AI分析']}

            </p>

            </div>

            <div style='text-align:right;'>

            <div style='color:{signal_color};
            font-weight:bold;
            margin-bottom:8px;'>

            {row['判定']}

            </div>

            <div style='color:white;
            font-size:13px;'>

            RSI:
            {row['RSI']}

            <br>

            PER:
            {row['PER']}

            <br>

            成長率:
            {row['売上成長率(%)']}%

            </div>

            </div>

            </div>

            </div>

            """, unsafe_allow_html=True)

    # =====================================
    # 銘柄選択
    # =====================================

    with tab2:

        if len(push_df) > 0:

            selected_stock = st.selectbox(
                "📈 チャートを見る銘柄",
                push_df["銘柄"]
            )

            selected_ticker = stock_list[
                stock_list["name"] == selected_stock
            ]["ticker"].values[0]

            period = st.selectbox(
                "📅 チャート期間",
                ["3mo", "6mo", "1y"],
                index=1
            )

            chart_hist = get_chart_data(
                selected_ticker,
                period
            )

            # =====================================
            # RSI計算
            # =====================================

            rsi_indicator = RSIIndicator(
                close=chart_hist["Close"]
            )

            chart_hist["RSI"] = rsi_indicator.rsi()

            # =====================================
            # チャート作成
            # =====================================

            fig, (ax_price, ax_rsi) = plt.subplots(
                2,
                1,
                figsize=(18, 10),
                gridspec_kw={"height_ratios": [4, 1]},
                sharex=True
            )

            # 背景色
            fig.patch.set_facecolor("#0E1117")

            ax_price.set_facecolor("#1A1D24")
            ax_rsi.set_facecolor("#1A1D24")

            # =====================================
            # 株価ライン
            # =====================================

            ax_price.plot(
                chart_hist.index,
                chart_hist["Close"],
                linewidth=2,
                color="#00FFAA",
                label="Close"
            )

            # MA25
            ax_price.plot(
                chart_hist.index,
                chart_hist["MA25"],
                linewidth=1.5,
                linestyle="--",
                color="#4DA3FF",
                label="MA25"
            )

            # タイトル
            ax_price.set_title(
                f"📈 {selected_stock}",
                color="white",
                fontsize=18
            )

            # 凡例
            ax_price.legend()

            # =====================================
            # RSI
            # =====================================

            ax_rsi.plot(
                chart_hist.index,
                chart_hist["RSI"],
                color="#00FFAA",
                linewidth=2
            )

            ax_rsi.axhline(
                70,
                color="#FF4B4B",
                linestyle="--"
            )

            ax_rsi.axhline(
                30,
                color="#4DA3FF",
                linestyle="--"
            )

            ax_rsi.set_ylim(0, 100)

            ax_rsi.set_title(
                "📉 RSI",
                color="white"
            )

            # =====================================
            # 現在価格
            # =====================================

            current_price = chart_hist["Close"].iloc[-1]

            ax_price.text(
                0.02,
                0.95,
                f"現在値: {current_price:.0f} 円",
                transform=ax_price.transAxes,
                fontsize=12,
                color="#00FFAA",
                verticalalignment="top",
                bbox=dict(
                    facecolor="#222",
                    edgecolor="#00FFAA",
                    boxstyle="round,pad=0.5"
                )
            )

            # =====================================
            # 文字色
            # =====================================

            for ax in [ax_price, ax_rsi]:

                ax.tick_params(colors="white")

                for spine in ax.spines.values():
                    spine.set_color("#444")

            # =====================================
            # レイアウト
            # =====================================

            plt.tight_layout()

            # =====================================
            # 表示
            # =====================================

            st.pyplot(
                fig,
                use_container_width=True
            )

        else:

            st.warning(
                "⚠️ 押し目候補がありません"
            )