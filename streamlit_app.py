import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# [설정] 관장님의 데이터 주소
# ==========================================
sheet_id = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

# 탭별 번호 (GID)
gid_students = "0"            # 원생명단
gid_guide = "1774705614"      # 기질가이드
gid_attendance = "244532436"  # 출석부
gid_schedule = "538477435"    # 심사일정

# ==========================================
# 1. 데이터 로드 엔진
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

@st.cache_data(ttl=0)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        # 시간 정렬을 위해 모든 데이터를 문자열(String)로 가져옵니다
        return pd.read_csv(url, dtype=str)
    except:
        return pd.DataFrame()

df_students = load_data(gid_students)
df_guide = load_data(gid_guide)
df_schedule = load_data(gid_schedule)

# ==========================================
# 2. 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    st.markdown("**System Ver 3.0**")
    st.markdown("---")
    
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚌 차량표 (시간순)",  # 업데이트됨
        "📝 출석부", 
        "🔍 기질 인사이트", 
        "💬 훈육 코치", 
        "📈 승급심사 관리",
        "🎂 이달의 생일"
    ])
    
    st.markdown("---")
    st.caption(f"접속일: {datetime.now().strftime('%Y-%m-%d')}")

# ==========================================
# 3. 기능 구현
# ==========================================

# [1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    st.header("📢 오늘의 작전 브리핑")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 오늘 심사 대상자 확인
    if not df_students.empty and '심사일시' in df_students.columns:
        df_students['심사일시'] = df_students['심사일시'].fillna('').astype(str).str.strip()
        today_test = df_students[df_students['심사일시'] == today]
        
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows():
                cur_level = row['현재급'] if '현재급' in row else '미입력'
                st.write(f" - **{row['이름']}** (현재: {cur_level})")
        else:
            st.success("✅ 오늘 예정된 심사는 없습니다.")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.warning("🌧️ [제주 날씨] 습도 높음! 안전 운행")
    c2.info("💡 차량 운행 시 창문 닫기 & 인원 체크")

# [2] 차량표 (업데이트: 이용여부 필터 + 시간순 정렬)
elif menu == "🚌 차량표 (시간순)":
    st.header("🚌 차량 운행 스케줄")
    
    # 필수 컬럼 확인
    required_cols = ['차량', '차량이용여부', '등원시간', '하원시간', '등원장소', '하원장소']
    missing = [c for c in required_cols if c not in df_students.columns]
    
    if not missing:
        # 1. 운행 모드 선택
        mode = st.radio("운행 모드", ["등원 (집→도장)", "하원 (도장→집)"], horizontal=True)
        
        # 2. 차량 선택
        car_list = sorted(df_students['차량'].dropna().unique().tolist())
        selected_car = st.selectbox("배차 선택", car_list)
        
        # 3. 데이터 필터링
        # (1) 해당 차량 탑승자
        target = df_students[df_students['차량'] == selected_car]
        
        # (2) 차량 이용 여부 체크 (O, 이용, 사용 등이 들어있으면 통과)
        # 'X', '미이용', 빈칸은 제외합니다.
        target = target[target['차량이용여부'].astype(str).str.contains('O|이용|사용', na=False)]
        
        # 4. 시간순 정렬 및 컬럼 설정
        if "등원" in mode:
            time_col = '등원시간'
            loc_col = '등원장소'
        else:
            time_col = '하원시간'
            loc_col = '하원장소' # 엑셀에 '하차장소'로 적으셨으면 여기를 '하차장소'로 고치세요
        
        # 데이터가 있으면 정렬 및 표시
        if not target.empty:
            # 시간 기준 오름차순 정렬 (NaN 값은 맨 뒤로)
            target = target.sort_values(by=time_col, ascending=True, na_position='last')
            
            st.write(f"### 🚍 {selected_car} {mode} 명단 ({len(target)}명)")
            
            # 보기 좋게 표 출력
            st.dataframe(
                target[[time_col, '이름', loc_col, '수련부']], 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"조건에 맞는 탑승자가 없습니다. ('차량이용여부'가 O인지 확인해주세요)")
            
    else:
        st.error(f"엑셀에 다음 제목이 빠져있습니다: {missing}")
        st.caption("구글 시트 1행(제목줄)을 확인해주세요.")

# [3] 출석부
elif menu == "📝 출석부":
    st.header("📝 수련부별 출석부")
    
    if '수련부' in df_students.columns:
        class_list = sorted(df_students['수련부'].dropna().unique().tolist())
        selected_class = st.selectbox("수련 시간 선택", class_list)
        
        class_students = df_students[df_students['수련부'] == selected_class]
        
        st.write(f"### 🥋 {selected_class} ({len(class_students)}명)")
        
        cols = st.columns(3)
        for i, row in class_students.iterrows():
            with cols[i % 3]:
                st.checkbox(f"{row['이름']}", key=f"att_{i}")
    else:
        st.error("'수련부' 컬럼이 없습니다.")

# [4] 기질 인사이트
elif menu == "🔍 기질 인사이트":
    st.header("🔍 기질 검색")
    name = st.text_input("이름 입력")
    if name:
        res = df_students[df_students['이름'] == name]
        if not res.empty:
            row = res.iloc[0]
            g_type = row['기질유형'] if '기질유형' in row else "미입력"
            st.success(f"**{name}** ({g_type})")
            
            if not df_guide.empty and '기질유형' in df_guide.columns:
                guide = df_guide[df_guide['기질유형'] == g_type]
                if not guide.empty:
                    g_row = guide.iloc[0]
                    st.info(f"특징: {g_row['핵심특징']}")
                    st.warning(f"지도법: {g_row['지도_DO(해라)']}")
        else:
            st.error("없는 이름입니다.")

# [5] 훈육 코치
elif menu == "💬 훈육 코치":
    st.header("💬 AI 훈육 코치")
    if not df_guide.empty:
        sel = st.selectbox("기질 선택", df_guide['기질유형'].unique())
        if st.button("솔루션 보기"):
            guide = df_guide[df_guide['기질유형'] == sel].iloc[0]
            st.code(guide['훈육_스크립트'])

# [6] 승급심사
elif menu == "📈 승급심사 관리":
    st.header("📈 승급심사 현황")
    if not df_students.empty and '심사일시' in df_students.columns:
        # 심사 날짜가 있는 아이들만 필터링
        df_test = df_students[df_students['심사일시'].notna() & (df_students['심사일시'] != '')]
        if not df_test.empty:
            st.dataframe(df_test[['심사일시', '이름', '현재급', '수련부']], use_container_width=True)
        else:
            st.info("예정된 심사자가 없습니다.")

# [7] 이달의 생일
elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일자")
    this_month = datetime.now().month
    st.subheader(f"{this_month}월의 주인공 🎉")
    
    if not df_students.empty and '생년월일' in df_students.columns:
        df_students['생년월일'] = pd.to_datetime(df_students['생년월일'], errors='coerce')
        b_kids = df_students[df_students['생년월일'].dt.month == this_month]
        
        if not b_kids.empty:
            st.balloons()
            for i, row in b_kids.iterrows():
                date_str = row['생년월일'].strftime('%m월 %d일')
                st.info(f"🎂 {row['이름']} ({date_str})")
        else:
            st.write("생일자가 없습니다.")
