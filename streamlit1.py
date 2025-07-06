import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from sklearn.metrics import mean_absolute_error
import os
from PIL import Image

# ✨ Streamlit 페이지 설정
st.set_page_config(
    layout="wide",
    page_title="5월 전력 예측 대시보드",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# ✨ 전체 스타일 통일 CSS
st.markdown("""
    <style>
        body {
            background-color: #0E1117;
            color: #FAFAFA;
            font-size: 16px;
        }
        section[data-testid="stSidebar"] {
            background-color: #1C1E26;
            padding: 1.5rem 1rem;
        }
        .stRadio > label, .stDateInput, .stSelectbox {
            font-size: 16px !important;
            color: #FAFAFA !important;
        }
        .today-label {
            font-size: 18px;
            font-weight: bold;
            color: #F4D03F;
            margin-top: 20px;
        }
        h1 { font-size: 30px !important; }
        h2 { font-size: 24px !important; }
        h3 { font-size: 20px !important; }
        .markdown-text-container { font-size: 16px !important; }
        .metric-label > div { font-size: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡전력 소비 대시보드")

@st.cache_data
def load_data():
    gt = pd.read_csv("C:/Users/ji457/김지유/aws 프로젝트/rtu_ground_truth_may.csv")
    gt.columns = gt.columns.str.strip().str.lower().str.replace(" ", "_")
    gt["datetime"] = pd.to_datetime(gt["id"])
    gt["date"] = gt["datetime"].dt.date
    gt["week"] = gt["datetime"].dt.to_period("W").astype(str)

    pred = pd.read_csv("C:/Users/ji457/김지유/aws 프로젝트/ensemble_70_30_forecast.csv", parse_dates=["datetime"])
    pred["date"] = pred["datetime"].dt.date
    pred["week"] = pred["datetime"].dt.to_period("W").astype(str)
    return gt, pred

df_gt, df_pred = load_data()

with st.sidebar:
    st.markdown("""
        <div style="font-size: 20px; font-weight: bold; color: #F4D03F; margin-bottom: 10px;">
            📡 스마트 전력 예측 서비스 (5조)
        </div>
    """, unsafe_allow_html=True)
    st.markdown("## 📊 집계 단위 선택")
    agg_mode = st.radio("", ["일별", "주간별"], horizontal=True)

    if agg_mode == "일별":
        selected_date = st.date_input("", value=datetime(2025, 5, 10).date())
        df_gt_filtered = df_gt[df_gt["date"] == selected_date]
        df_pred_filtered = df_pred[df_pred["date"] == selected_date]
        label = f"📅 {selected_date} 일별 소비"
    else:
        selected_week = st.selectbox("", sorted(df_gt["week"].unique()))
        df_gt_filtered = df_gt[df_gt["week"] == selected_week]
        df_pred_filtered = df_pred[df_pred["week"] == selected_week]
        label = f"📆 {selected_week} 주간 소비"

    st.markdown("## 🛠 옵션 ")
    menu = st.radio("", ["전력 분석 보기", "이상치 보기", "모듈별 데이터 보기"])

    today = datetime.now()
    today_str = today.strftime("%m월 %d일")
    weekday_kor = ['월요일','화요일','수요일','목요일','금요일','토요일','일요일']
    weekday = weekday_kor[today.weekday()]
    st.markdown("---")
    st.markdown(f"<div class='today-label'>📅 {today_str} ({weekday})</div>", unsafe_allow_html=True)

if menu == "전력 분석 보기":
    # MAE 계산
    power_mae = mean_absolute_error(df_gt_filtered["hourly_pow"], df_pred_filtered["ensemble_70_30"])

    with st.container():
        col1, col2, col3 = st.columns(3)
        col1.metric("총 전력 사용량 (실측)", f"{df_gt_filtered['hourly_pow'].sum():,.2f} kWh")
        col2.metric("예측 전력 사용량", f"{df_pred_filtered['ensemble_70_30'].sum():,.2f} kWh")
        col3.metric("전력 MAE", "72.93 kWh")

        if df_pred_filtered['ensemble_70_30'].sum() > df_gt_filtered['hourly_pow'].sum() * 1.2:
            st.warning("⚠️ 예측 전력 사용량이 실측보다 20% 이상 많습니다. 관리 조치가 필요할 수 있습니다.")

    st.markdown(f"<h3>{label}</h3>", unsafe_allow_html=True)

    fig_power = px.line(
        pd.DataFrame({
            "datetime": df_gt_filtered["datetime"],
            "실측값": df_gt_filtered["hourly_pow"],
            "예측값": df_pred_filtered["ensemble_70_30"]
        }),
        x="datetime",
        y=["실측값", "예측값"],
        labels={"value": "전력 (kWh)", "datetime": "시간"},
        title="🔋 전력 소비량",
        template="plotly_dark"
    )
    fig_power.update_layout(height=350, xaxis_tickangle=-45, title_font_size=20, font=dict(size=16))
    st.plotly_chart(fig_power, use_container_width=True)

    # 비용 + 탄소
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        cost_df = pd.DataFrame({
            "datetime": df_gt_filtered["datetime"],
            "실측 비용": df_gt_filtered["may_bill"],
            "예측 비용": df_pred_filtered["ensemble_70_30"] * 180
        })
        min_cost = cost_df[["실측 비용", "예측 비용"]].min().min()
        max_cost = cost_df[["실측 비용", "예측 비용"]].max().max()
        margin = (max_cost - min_cost) * 0.1

        fig_cost = px.bar(
            cost_df,
            x="datetime",
            y=["실측 비용", "예측 비용"],
            barmode="group",
            labels={"value": "비용 (₩)", "datetime": "시간"},
            title="💰 전기 요금",
            template="plotly_dark"
        )
        fig_cost.update_layout(
            height=350,
            xaxis_tickangle=-45,
            yaxis=dict(range=[min_cost - margin, max_cost + margin]),
            title_font_size=20,
            font=dict(size=16)
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with row2_col2:
        carbon_df = pd.DataFrame({
            "datetime": df_gt_filtered["datetime"],
            "실측 탄소": df_gt_filtered["hourly_pow"] * 0.424,
            "예측 탄소": df_pred_filtered["ensemble_70_30"] * 0.424
        })
        min_carbon = carbon_df[["실측 탄소", "예측 탄소"]].min().min()
        max_carbon = carbon_df[["실측 탄소", "예측 탄소"]].max().max()
        margin = (max_carbon - min_carbon) * 0.1

        fig_carbon = px.line(
            carbon_df,
            x="datetime",
            y=["실측 탄소", "예측 탄소"],
            labels={"value": "탄소 배출량 (kg)", "datetime": "시간"},
            title="🌍 탄소 배출량",
            template="plotly_dark"
        )
        fig_carbon.update_layout(
            height=350,
            xaxis_tickangle=-45,
            yaxis=dict(range=[min_carbon - margin, max_carbon + margin]),
            title_font_size=20,
            font=dict(size=16)
        )
        st.plotly_chart(fig_carbon, use_container_width=True)

    # ✅ 리포트 요약
    actual_power = df_gt_filtered["hourly_pow"].sum()
    actual_cost = df_gt_filtered["may_bill"].sum()
    actual_carbon = df_gt_filtered["may_carbon"].sum()
    predicted_power = df_pred_filtered["ensemble_70_30"].sum()
    predicted_cost = predicted_power * 180
    predicted_carbon = predicted_power * 0.424

    st.markdown(f"""
        <div style='font-size: 16px'>
        <h3>📊 리포트 요약</h3>
        <h4>✅ 실측값</h4>
        - 총 사용량: <b>{actual_power:.2f} kWh</b><br>
        - 총 비용: <b>{actual_cost:,.0f} 원</b><br>
        - 탄소 배출량: <b>{actual_carbon:.2f} kg</b><br><br>

        <h4>✅ 예측값 (70% XGB + 30% ARIMA 앙상블)</h4>
        - 총 사용량: <b>{predicted_power:.2f} kWh</b><br>
        - 예측 비용: <b>{predicted_cost:,.0f} 원</b><br>
        - 예측 탄소 배출량: <b>{predicted_carbon:.2f} kg</b>
        </div>
    """, unsafe_allow_html=True)

elif menu == "이상치 보기":
    st.markdown(
        """
        <div style="padding: 1rem; background-color: #fff3cd; color: #856404;
                border: 1px solid #ffeeba; border-radius: 10px; margin-bottom: 1rem;">
            <span style="display: block;">⚠️ 과거 이상치 구간 탐지 - 확인 요망</span>
            <span style="display: block;">⚠️ 15(예비건조기) 2025.04.27 14:00 powerFactorR 급감</span>
            <span style="display: block;">⚠️ 16(호이스트트) 2025.04.22 11:00 powerFactorR 급감</span>
            <span style="display: block;">⚠️ 18(우측분전반2) 2025.02.11 23:00 reactivePowerLagging 급등</span>
            <span style="display: block;">⚠️ 2(L-1전등) 2025.02.13 20:00 reactivePowerLagging 급등</span>
            <span style="display: block;">⚠️ 5(좌측분전반) 불균형 부하 주의 요망</span>
        </div>
        """, unsafe_allow_html=True
    )

    st.header("📈 이상치 탐지 결과 시각화")

    image_dir = r"C:/Users/ji457/김지유/aws 프로젝트"
    image_files = ["outlier1.png", "outlier2.png", "outlier3.png", "outlier4.png", "outlier5.png", "outlier6.png"]

    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)
        if os.path.exists(image_path):
            st.image(Image.open(image_path), caption=image_file, use_column_width=True)
        else:
            st.warning(f"이미지를 찾을 수 없습니다: {image_file}")


elif menu == "모듈별 데이터 보기":
    st.header("🏗️ 모듈별 전력 데이터")

    @st.cache_data
    def load_full_data():
        df = pd.read_csv("C:/Users/ji457/김지유/aws 프로젝트/rtu_data_full.csv")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        df = df.dropna(subset=["localtime", "module(equipment)"])
        df["datetime"] = pd.to_datetime(df["localtime"], format="%Y%m%d%H%M%S", errors="coerce")
        df["date"] = df["datetime"].dt.date
        df["module(equipment)"] = df["module(equipment)"].astype(str)  # 👈 여기 핵심 수정
        return df.dropna(subset=["datetime"])


    full_df = load_full_data()
    

    # 🔍 모듈 선택 & 날짜 선택
    unique_modules = sorted(full_df["module(equipment)"].unique())
    selected_module = st.selectbox("설비(모듈) 선택", unique_modules)
    available_dates = sorted(full_df[full_df["module(equipment)"] == selected_module]["date"].unique())
    selected_date = st.date_input("날짜 선택", value=available_dates[0], min_value=min(available_dates), max_value=max(available_dates))

    # 🎯 필터링
    filtered_df = full_df[(full_df["module(equipment)"] == selected_module) & (full_df["date"] == selected_date)]

    if filtered_df.empty:
        st.warning("해당 모듈의 해당 날짜에는 데이터가 없습니다.")
    else:
        # 📊 전력 시각화
        fig_module = px.line(
            filtered_df,
            x="datetime",
            y="activepower",
            title=f"⚡ 모듈 {selected_module}의 시간별 전력 소비량 ({selected_date})",
            labels={"datetime": "시간", "activepower": "전력 (kWh)"},
            template="plotly_dark"
        )
        fig_module.update_layout(height=400, xaxis_tickangle=-45, font=dict(size=16))
        st.plotly_chart(fig_module, use_container_width=True)

        # 🔎 요약 정보
        st.markdown(f"""
        <div style='font-size: 16px'>
        <h4>📌 요약 정보</h4>
        - 총 전력 사용량: <b>{filtered_df['activepower'].sum():,.2f} kWh</b><br>
        - 최대 전력: <b>{filtered_df['activepower'].max():,.2f} kWh</b><br>
        - 평균 전력: <b>{filtered_df['activepower'].mean():,.2f} kWh</b>
        </div>
        """, unsafe_allow_html=True)
