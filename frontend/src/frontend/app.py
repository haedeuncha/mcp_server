import requests
import streamlit as st

from frontend.config import BACKEND_URL

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️")
st.title("Weather Dashboard")

with st.form("weather"):
    city = st.text_input("도시", value="서울")
    day = st.radio("날짜", options=["today", "tomorrow"], index=1, horizontal=True,
                   format_func=lambda d: "오늘" if d == "today" else "내일")
    submitted = st.form_submit_button("날씨 조회")

if submitted:
    try:
        response = requests.get(f"{BACKEND_URL}/weather", params={"city": city, "day": day}, timeout=20)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            st.warning(f"'{city}' 도시를 찾을 수 없어요.")
        else:
            st.subheader(f"{data['city']} ({data.get('country') or ''}) · {data['date']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("최고 기온", f"{data['temperature_max']}°C")
            c2.metric("최저 기온", f"{data['temperature_min']}°C")
            c3.metric("강수 확률", f"{data['precipitation_probability']}%")
            st.caption(("⚡ Redis 캐시" if data.get("cached") else "🌐 MCP 서버 조회") + f" · 출처 {data.get('source')}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"날씨 조회 실패: {exc}")

st.divider()
st.subheader("최근 조회 기록")
try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=5).json()
    st.caption(f"redis: {health.get('redis')} · database: {health.get('database')}")
    items = requests.get(f"{BACKEND_URL}/history", params={"limit": 10}, timeout=5).json().get("items", [])
    if items:
        st.dataframe(
            [{"시간": i["created_at"][:19].replace("T", " "), "도시": i["city"], "날짜": i["day"],
              "캐시": "✓" if i["cached"] else "", "최고": i["result"].get("temperature_max"),
              "최저": i["result"].get("temperature_min")} for i in items],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("기록이 없거나 DB가 연결되지 않았어요.")
except Exception as exc:  # noqa: BLE001
    st.caption(f"백엔드에 연결할 수 없어요: {exc}")
