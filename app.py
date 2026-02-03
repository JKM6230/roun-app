import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# ==========================================
# [정석] 구글 시트 전체 주소 (수정 금지)
# 관장님이 주신 주소를 그대로 사용합니다.
# ==========================================
url = "https://docs.google.com/spreadsheets/d/1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo/edit"

# ==========================================
# 1. 기본 설정 및 연결
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

# 디자인 적용
st.markdown("""
    <style>
    .main-header {font-size: 1.8rem; color: #1E3A8A; font-weight: 700; margin-bottom: 10px;}
    .alert-box {background-color: #FEF2F2; border: 1px solid #EF4444; padding: 10px; border-radius: 5px; color: #991B1B;}
    </style>
""", unsafe_allow_html=True)

# 스트림릿 전용 연결 엔진 가동 (정석 방법)
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. 데이터 불러오기 (탭 이름으로 찾기)
# ==========================================
@st.cache_data(ttl=60) # 60초마다 데이터 갱신
def load_all_data():
    try:
        # worksheet="탭이름" 으로 정확하게 가져옵니다.
        df_1 = conn.read(spreadsheet=url, worksheet="원생명단")
        df_2 = conn.read(spreadsheet=url, worksheet="기질가이드")
        df_3 = conn.read(spreadsheet=url, worksheet="심사일정")
        return df_1, df_2, df_3
    except Exception as e:
        return None, None, None

df_students, df_guide, df_schedule = load_all_data()

# 데이터 로드 실패 시 안내
if df_students is None:
    st.error("🚨 데이터를 불러오지 못했습니다.")
    st.info("1. 구글 시트의 탭 이름이 [원생명단, 기질가이드, 심사일정] 인지 확인해주세요.\n2. 구글 시트 우측 상단 [공유]가 '링크가 있는 모든 사용자'인지 확인해주세요.")
    st.stop()

# ==========================================
# 3. 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.header("🥋 로운태권도 파트너")
    menu = st.radio("메뉴 선택", ["🏠 홈 대시보드", "🚍 출석/차량", "🔍 기질 인사이트", "💬 훈육 코치", "📈 승급 심사"])
    st.divider()
    st.caption(f"접속일: {datetime.now().strftime('%Y-%m-%d')}")

# ==========================================
# 4. 기능 구현
# ==========================================

# [탭 1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    st.markdown('<div class="main-header">📢 오늘의 작전 브리핑</div>', unsafe_allow_html=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not df_schedule.empty and '날짜' in df_schedule.columns:
        today_shimsa = df_schedule[df_schedule['날짜'].astype(str) == today]
        if not today_shimsa.empty:
            st.markdown(f"""
            <div class="alert-box">
                <b>🔥 오늘 승급심사 도전자: {len(today_shimsa)}명</b><br>
                {', '.join(today_shimsa['이름'].tolist())}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("✅ 오늘은 예정된 심사가 없습니다.")
            
    col1, col2 = st.columns(2)
    with col1:
        st.warning("🌧️ [제주 날씨] 습도 높음! 매트 미끄럼 주의")
    with col2:
        st.success("🚍 차량 운행 시 '슬리핑 차일드 체크' 필수")

# [탭 2] 출석/차량
elif menu == "🚍 출석/차량":
    st.markdown('<div class="main-header">🚍 실시간 차량 & 출석</div>', unsafe_allow_html=True)
    
    if '차량' in df_students.columns:
        car_select = st.selectbox("차량 선택", ["1호차", "2호차", "도보"])
        filtered_df = df_students[df_students['차량'] == car_select]
        
        st.write(f"### {car_select} 탑승 명단")
        for idx, row in filtered_df.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{row['이름']}** ({row['하차장소']})")
            with col2:
                st.checkbox("하차", key=f"check_{idx}")
    else:
        st.error("원생명단 시트에 '차량' 칸이 없습니다.")

# [탭 3] 기질 인사이트
elif menu == "🔍 기질 인사이트":
    st.markdown('<div class="main-header">🔍 원생 기질 검색</div>', unsafe_allow_html=True)
    name = st.text_input("이름 검색")
    
    if name:
        student = df_students[df_students['이름'] == name]
        if not student.empty:
            s_data = student.iloc[0]
            if '기질유형' in s_data:
                g_type = s_data['기질유형']
                
                guide_match = df_guide[df_guide['기질유형'] == g_type]
                if not guide_match.empty:
                    guide = guide_match.iloc[0]
                    st.success(f"찾았습니다! **{s_data['이름']}** ({g_type})")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info(f"**💎 핵심 특징**\n{guide['핵심특징']}")
                        st.write(f"**⚡ 에너지원:** {guide['에너지원']}")
                    with c2:
                        st.warning(f"**⭕ 지도법 (DO)**\n{guide['지도_DO(해라)']}")
                        st.error(f"**❌ 주의사항 (DON'T)**\n{guide['지도_DONT(하지마라)']}")
                else:
                    st.warning("기질 가이드 정보가 없습니다.")
            else:
                st.error("원생명단에 '기질유형' 정보가 없습니다.")
        else:
            st.error("등록되지 않은 이름입니다.")

# [탭 4] 훈육 코치
elif menu == "💬 훈육 코치":
    st.markdown('<div class="main-header">💬 AI 훈육 스크립트</div>', unsafe_allow_html=True)
    
    types = df_guide['기질유형'].unique()
    sel_type = st.selectbox("아이의 기질을 선택하세요", types)
    
    if st.button("스크립트 보기"):
        guide = df_guide[df_guide['기질유형'] == sel_type].iloc[0]
        st.markdown(f"### 💡 {sel_type} 아이를 위한 대화법")
        st.code(guide['훈육_스크립트'])

# [탭 5] 승급 심사
elif menu == "📈 승급 심사":
    st.markdown('<div class="main-header">📈 자기주도 심사 관리</div>', unsafe_allow_html=True)
    st.write("### 📋 예정된 심사 목록")
    st.dataframe(df_schedule, use_container_width=True)
