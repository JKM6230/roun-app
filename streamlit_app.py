import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# [설정 완료] 관장님이 알려주신 ID와 번호를 심어뒀습니다!
# ==========================================
sheet_id = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

# 탭별 고유 번호(GID)
gid_students = "0"            # 원생명단
gid_guide = "1774705614"      # 기질가이드
gid_attendance = "244532436"  # 출석부
gid_schedule = "538477435"    # 심사일정

# ==========================================
# 1. 기본 설정 및 데이터 로드 함수 (만능 키 방식)
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

# 로딩 속도 최적화 (ttl=0: 항상 최신 데이터 가져오기)
@st.cache_data(ttl=0)
def load_data(sheet_id, gid):
    # 구글 시트를 강제로 CSV(표)로 변환해서 가져오는 주소
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        # 에러가 나면 빈 표를 반환
        return pd.DataFrame()

# ==========================================
# 2. 데이터 불러오기 (실패 시 원인 분석 메시지 출력)
# ==========================================
df_students = load_data(sheet_id, gid_students)
df_guide = load_data(sheet_id, gid_guide)
df_schedule = load_data(sheet_id, gid_schedule)
df_attendance = load_data(sheet_id, gid_attendance)

# [진단] 데이터가 텅 비었는지 확인
if df_students.empty:
    st.error("🚨 **데이터 연결 실패! (SOS)**")
    st.warning("관장님, **구글 시트 공유 설정**이 아직 닫혀있는 것 같습니다.")
    st.info("👉 구글 시트 우측 상단 [공유] 버튼 클릭 → **'링크가 있는 모든 사용자'**로 되어있는지 꼭 확인해주세요.")
    st.stop() # 여기서 멈춤

# ==========================================
# 3. 화면 디자인 (사이드바)
# ==========================================
with st.sidebar:
    st.header("🥋 로운태권도 파트너")
    st.markdown("---")
    menu = st.radio("메뉴 선택", ["🏠 홈 대시보드", "🚍 출석/차량", "🔍 기질 인사이트", "💬 훈육 코치", "📈 승급 심사"])
    st.markdown("---")
    st.caption(f"접속일: {datetime.now().strftime('%Y-%m-%d')}")

# ==========================================
# 4. 기능 구현
# ==========================================

# [탭 1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    st.title("📢 오늘의 작전 브리핑")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 심사 일정 확인
    if not df_schedule.empty and '날짜' in df_schedule.columns:
        # 날짜 형식을 문자로 통일해서 비교
        today_shimsa = df_schedule[df_schedule['날짜'].astype(str) == today]
        
        if not today_shimsa.empty:
            st.error(f"🔥 **오늘 승급심사 도전자: {len(today_shimsa)}명**")
            for idx, row in today_shimsa.iterrows():
                st.write(f"- **{row['이름']}** (목표: {row['목표급수']})")
        else:
            st.success("✅ 오늘은 예정된 심사가 없습니다.")
    else:
        st.info("📅 심사 일정 데이터가 없습니다.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.warning("🌧️ [제주 날씨] 습도 높음! 매트 미끄럼 주의")
    with col2:
        st.info("🚍 차량 운행 시 '슬리핑 차일드 체크' 필수")

# [탭 2] 출석/차량
elif menu == "🚍 출석/차량":
    st.title("🚍 실시간 차량 & 출석")
    
    if not df_students.empty and '차량' in df_students.columns:
        car_list = ["1호차", "2호차", "도보"]
        car_select = st.selectbox("차량 선택", car_list)
        
        # 선택한 차량만 필터링
        filtered_df = df_students[df_students['차량'] == car_select]
        
        if not filtered_df.empty:
            st.write(f"### {car_select} 탑승 명단 ({len(filtered_df)}명)")
            for idx, row in filtered_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{row['이름']}** ({row['하차장소']})")
                with col2:
                    st.checkbox("하차", key=f"check_{idx}")
        else:
            st.write("탑승 인원이 없습니다.")
    else:
        st.error("원생 명단에 '차량' 정보가 없습니다.")

# [탭 3] 기질 인사이트
elif menu == "🔍 기질 인사이트":
    st.title("🔍 원생 기질 검색")
    name = st.text_input("아이 이름을 입력하세요 (예: 김지안)")
    
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
                        st.warning(f"'{g_type}' 기질에 대한 가이드가 엑셀에 없습니다.")
                else:
                    st.error("기질 가이드 데이터를 불러오지 못했습니다.")
            else:
                st.error("명단에 '기질유형' 칸이 비어있습니다.")
        else:
            st.error("등록된 원생이 아닙니다.")

# [탭 4] 훈육 코치
elif menu == "💬 훈육 코치":
    st.title("💬 AI 훈육 스크립트")
    
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
    st.title("📈 자기주도 심사 관리")
    
    if not df_schedule.empty:
        st.write("### 📋 예정된 심사 목록")
        st.dataframe(df_schedule, use_container_width=True)
    else:
        st.write("등록된 심사 일정이 없습니다.")
