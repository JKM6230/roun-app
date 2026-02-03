import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# [설정 완료] 관장님의 구글 시트 ID & 탭 번호
# ==========================================
sheet_id = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

# 탭별 고유 번호(GID) - 관장님이 알려주신 번호 그대로 적용
gid_students = "0"            # 원생명단
gid_guide = "1774705614"      # 기질가이드
gid_attendance = "244532436"  # 출석부
gid_schedule = "538477435"    # 심사일정

# ==========================================
# 1. 기본 설정 및 데이터 로드 함수 (Direct CSV 방식)
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

# 디자인(CSS)
st.markdown("""
    <style>
    .main-header {font-size: 1.8rem; color: #1E3A8A; font-weight: 700; margin-bottom: 10px;}
    .alert-box {background-color: #FEF2F2; border: 1px solid #EF4444; padding: 10px; border-radius: 5px; color: #991B1B;}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60) # 60초마다 새로고침
def load_data(sheet_id, gid):
    # 구글 시트를 강제로 CSV 파일로 변환해서 읽어오는 강력한 주소
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        # 에러가 나면 빈 표를 반환하고 에러 내용은 숨김
        return pd.DataFrame()

# ==========================================
# 2. 데이터 불러오기
# ==========================================
df_students = load_data(sheet_id, gid_students)
df_guide = load_data(sheet_id, gid_guide)
df_schedule = load_data(sheet_id, gid_schedule)
df_attendance = load_data(sheet_id, gid_attendance)

# [진단] 데이터가 잘 왔는지 확인
if df_students.empty:
    st.error("🚨 데이터 연결 실패!")
    st.info("구글 시트 우측 상단 [공유] 버튼을 눌러 **'링크가 있는 모든 사용자'**로 되어있는지 꼭 확인해주세요.")
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
    
    # 심사 일정 확인
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
    else:
        st.info("📅 심사 일정 데이터가 없습니다.")

    col1, col2 = st.columns(2)
    with col1:
        st.warning("🌧️ [제주 날씨] 습도 높음! 매트 미끄럼 주의")
    with col2:
        st.success("🚍 차량 운행 시 '슬리핑 차일드 체크' 필수")

# [탭 2] 출석/차량
elif menu == "🚍 출석/차량":
    st.markdown('<div class="main-header">🚍 실시간 차량 & 출석</div>', unsafe_allow_html=True)
    
    if not df_students.empty and '차량' in df_students.columns:
        car_list = df_students['차량'].unique()
        car_select = st.selectbox("차량 선택", car_list)
        
        filtered_df = df_students[df_students['차량'] == car_select]
        
        st.write(f"### {car_select} 탑승 명단")
        for idx, row in filtered_df.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{row['이름']}** ({row['하차장소']})")
            with col2:
                st.checkbox("하차", key=f"check_{idx}")
    else:
        st.error("원생 명단에 '차량' 정보가 없습니다.")

# [탭 3] 기질 인사이트
elif menu == "🔍 기질 인사이트":
    st.markdown('<div class="main-header">🔍 원생 기질 검색</div>', unsafe_allow_html=True)
    name = st.text_input("이름 검색 (예: 김지안)")
    
    if name:
        student = df_students[df_students['이름'] == name]
        if not student.empty:
            s_data = student.iloc[0]
            if '기질유형' in s_data:
                g_type = s_data['기질유형']
                
                # 기질 가이드 매칭
                if not df_guide.empty and '기질유형' in df_guide.columns:
                    guide_match = df_guide[df_guide['기질유형'] == g_type]
                    if not guide_match.empty:
                        guide = guide_match.iloc[0]
                        st.success(f"찾았습니다! **{s_data['이름']}** ({g_type})")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.info(f"**💎 핵심 특징**\n\n{guide['핵심특징']}")
                            st.write(f"**⚡ 에너지원:** {guide['에너지원']}")
                        with c2:
                            st.warning(f"**⭕ 지도법 (DO)**\n\n{guide['지도_DO(해라)']}")
                            st.error(f"**❌ 주의사항 (DON'T)**\n\n{guide['지도_DONT(하지마라)']}")
                    else:
                        st.warning(f"'{g_type}' 기질에 대한 가이드가 없습니다.")
                else:
                    st.error("기질 가이드 데이터를 불러오지 못했습니다.")
            else:
                st.error("명단에 '기질유형'이 적혀있지 않습니다.")
        else:
            st.error("등록된 원생이 아닙니다.")

# [탭 4] 훈육 코치
elif menu == "💬 훈육 코치":
    st.markdown('<div class="main-header">💬 AI 훈육 스크립트</div>', unsafe_allow_html=True)
    
    if not df_guide.empty and '기질유형' in df_guide.columns:
        types = df_guide['기질유형'].unique()
        sel_type = st.selectbox("아이의 기질을 선택하세요", types)
        
        if st.button("스크립트 보기"):
            guide = df_guide[df_guide['기질유형'] == sel_type].iloc[0]
            st.markdown(f"### 💡 {sel_type} 아이를 위한 대화법")
            st.code(guide['훈육_스크립트'])
    else:
        st.error("기질 가이드 데이터가 없습니다.")

# [탭 5] 승급 심사
elif menu == "📈 승급 심사":
    st.markdown('<div class="main-header">📈 자기주도 심사 관리</div>', unsafe_allow_html=True)
    
    if not df_schedule.empty:
        st.write("### 📋 예정된 심사 목록")
        st.dataframe(df_schedule, use_container_width=True)
    else:
        st.write("등록된 심사 일정이 없습니다.")
