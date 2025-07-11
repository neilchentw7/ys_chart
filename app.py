
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import os

# 載入中文字體
ch_font = FontProperties(fname="fonts/NotoSansTC-Black.ttf")
font_name = ch_font.get_name()
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="混凝土強度管制圖", layout="wide")

st.title("🔎 混凝土抗壓強度管制圖工具")
st.sidebar.image("logo.png", width=100)

st.sidebar.text(f"目前使用字體: {font_name}")

# 範例下載
example_csv = '''取樣日期,組號,施工部位,X1,X2,X3,X4,X5,X6
2024/06/01,1,主橋#1,680,700,695,,,,
2024/06/02,2,主橋#2,720,735,710,715,,
2024/06/03,3,主橋#3,640,630,650,,,,
'''
st.download_button("📥 下載範例 CSV", data=example_csv.encode("utf-8-sig"),
                   file_name="example.csv", mime="text/csv")

# 使用者輸入設計強度
fc = st.sidebar.number_input("規定強度 fc' (kg/cm²)", value=420)
fcr = st.sidebar.number_input("目標強度 fcr' (kg/cm²)", value=525)

uploaded = st.file_uploader("📤 上傳混凝土強度 CSV", type="csv")
if uploaded:
    df = pd.read_csv(uploaded)
    st.success("資料載入成功！")

    base_cols = {"取樣日期", "組號", "施工部位"}
    strength_cols = [c for c in df.columns if c.startswith("X")]
    if not base_cols.issubset(df.columns):
        st.error("需至少有欄位：取樣日期, 組號, 施工部位, 以及 X1~X6")
        st.stop()

    df["X"] = df[strength_cols].mean(axis=1, skipna=True)
    df["R"] = df[strength_cols].max(axis=1, skipna=True) - df[strength_cols].min(axis=1, skipna=True)

    st.subheader("📋 資料預覽")

# 自動根據資料筆數設定高度（每筆約 35 像素 + 表頭）
    num_rows = df.shape[0]
    calculated_height = min(1200, 40 + num_rows * 35)  # 上限 1200 避免過長

    st.dataframe(
    df[["取樣日期", "組號", "施工部位"] + strength_cols + ["X", "R"]],
    use_container_width=True,
    height=calculated_height
    )
    # 圖表
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    axes[0].plot(df["取樣日期"], df["X"], marker="o", label="X (平均)")
    axes[0].axhline(fc, ls="--", color="red", label="fc'")
    axes[0].axhline(fcr, ls="--", color="green", label="fcr'")
    axes[0].set_title("個別值強度管制圖", fontproperties=ch_font)
    axes[0].set_xlabel("取樣日期", fontproperties=ch_font)
    axes[0].set_ylabel("抗壓強度 (kg/cm²)", fontproperties=ch_font)
    axes[0].legend(prop=ch_font)

    df["Xbar5"] = df["X"].rolling(5).mean()
    axes[1].plot(df["取樣日期"], df["Xbar5"], marker="o", color="orange")
    axes[1].axhline(fc, ls="--", color="red")
    axes[1].axhline(fcr, ls="--", color="green")
    axes[1].set_title("5 組移動平均管制圖", fontproperties=ch_font)
    axes[1].set_xlabel("取樣日期", fontproperties=ch_font)
    axes[1].set_ylabel("平均強度", fontproperties=ch_font)

    axes[2].plot(df["取樣日期"], df["R"], marker="o", color="black")
    axes[2].axhline(df["R"].mean(), ls="--", color="blue")
    axes[2].set_title("組內強度全距圖 (R chart)", fontproperties=ch_font)
    axes[2].set_xlabel("取樣日期", fontproperties=ch_font)
    axes[2].set_ylabel("全距 R", fontproperties=ch_font)

    for ax in axes:
        ax.tick_params(axis='x', rotation=30)
    plt.tight_layout()
    st.pyplot(fig)

    # 統計分析
    Xbar = df["X"].mean()
    S = df["X"].std()
    V1 = df["R"].mean() / Xbar * 100
    V_percent = S / Xbar * 100
    safety = Xbar / fc
    achieve = Xbar / fcr

    def classify_std(s):
        if s < 28: return "變異極小，控制極佳"
        elif s < 35: return "變異小，表現穩定"
        elif s < 42: return "變異屬正常"
        else: return "變異略大，部分點波動需留意"

    def classify_v1(v):
        if v <= 3: return "最佳級，取樣一致性極佳"
        elif v <= 4: return "很好級，取樣一致性良好"
        elif v <= 6: return "正常級，變異可接受"
        else: return "不良級，建議加強取樣穩定性"

    def classify_v_percent(vp):
        if vp <= 6:
            return "最佳級，整體製程極穩定"
        elif vp <= 8:
            return "良好級，整體波動小"
        elif vp <= 10:
            return "正常級，建議持續觀察"
        else:
            return "偏高級，建議檢討原料/施工波動"

    def classify_safety(r):
        if r >= 1.2: return "強度安全性高"
        elif r >= 1.1: return "強度足夠，略保守"
        else: return "強度接近設計下限，建議留意"

    def classify_economy(r):
        if r >= 1.2: return "強度過高，可能配比偏保守"
        elif r >= 1.05: return "強度達標，配比偏穩健"
        else: return "強度接近目標邊緣，風險需控管"

    # 結論區
    st.markdown("---")
    st.subheader("📌 分析結論")
    st.markdown(f"""
- 平均強度 X̄: **{Xbar:.1f} kg/cm²**
- 標準差 S: **{S:.1f} kg/cm²**, {classify_std(S)}
- 組內變異係數 V1: **{V1:.1f}%**, {classify_v1(V1)}
- 安全係數 (X̄ / fc'): **{safety:.2f}**, {classify_safety(safety)}
- 達成率 (X̄ / fcr'): **{achieve:.2f}**, {classify_economy(achieve)}
- 整體變異係數 V%: **{V_percent:.1f}%**, {classify_v_percent(V_percent)}
""")

    # 補充參考表
    st.markdown("---")
    st.subheader("📘 變異指標參考表")

    st.markdown("#### V₁ 組內變異係數")
    st.markdown("""
| V₁ (%) 範圍 | 評等 | 說明 |
|-------------|------|------|
| ≤ 3.0%      | 最佳級 | 取樣一致性極佳 |
| 3.0 ~ 4.0%  | 很好級 | 取樣一致性良好 |
| 4.0 ~ 6.0%  | 正常級 | 可接受，變異中等 |
| > 6.0%      | 不良級 | 建議加強取樣穩定性 |
""")

    st.markdown("#### V% 整體變異係數")
    st.markdown("""
| V% 範圍     | 評等   | 說明 |
|-------------|--------|------|
| ≤ 6.0%      | 最佳級 | 整體製程非常穩定 |
| 6.0 ~ 8.0%  | 良好級 | 整體波動低 |
| 8.0 ~ 10.0% | 正常級 | 建議持續觀察 |
| > 10.0%     | 偏高級 | 建議檢討原料或施工變異 |
""")
st.markdown("### 🖨️ 匯出與列印")
st.markdown("""
按下以下按鈕，即可列印整個畫面（包含圖表與結論）：

<button onclick="window.print()">🖨️ 列印本頁</button>
""", unsafe_allow_html=True)