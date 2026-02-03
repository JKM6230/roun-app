import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# [설정] 관장님의 데이터 주소
# ==========================================
sheet_id = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

# 탭별 고유 번호 (GID)
gid_students = "0"            # 원생명단
gid_notice = "1622401395"     # 공지사항
gid_guide = "1774705614"      # 기질가이드
gid_attendance = "244532436"  # 출석부 (기록용 X, 조회용)

# ==========================================
# 1. 데이터 로드 엔진
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

@st.cache_data(ttl=0)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        return pd.read_csv(url, dtype=str)
    except:
        return pd.DataFrame()

df_students = load_data(gid_students)
df_notice = load_data(gid_notice)
df_guide = load_data(gid_guide)

# ==========================================
# 2. 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    st.markdown("**System Ver 7.0 (Final)**")
    st.markdown("---")
    
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚍 차량 운행표", 
        "📝 수련부 출석", 
        "🔍 기질 인사이트", 
        "💬 훈육 코치", 
        "📈 승급심사 관리",
        "🎂 이달의 생일"
    ])
    
    st.markdown("---")
    st.caption(f"접속일: {datetime.now().strftime('%Y-%m-%d')}")
    if st.button("🔄 새로고침 (초기화)"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 기능 구현
# ==========================================

# [1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    st.header("📢 오늘의 작전 브리핑")
    
    if not df_notice.empty:
        try:
            latest = df_notice.iloc[-1]
            st.info(f"**[공지 | {latest[0]}]**\n\n{latest[1]}")
        except:
            st.warning("공지사항 데이터 형식 확인 필요")
    else:
        st.info("등록된 공지사항이 없습니다.")

    st.markdown("---")
    
    today = datetime.now().strftime("%Y-%m-%d")
    if not df_students.empty and '심사일시' in df_students.columns:
        df_students['심사일시'] = df_students['심사일시'].fillna('').astype(str).str.strip()
        today_test = df_students[df_students['심사일시'] == today]
        
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows():
                level = row.get('단', row.get('현재급', '-'))
                st.write(f" - **{row['이름']}** (현재: {level})")
        else:
            st.success("✅ 오늘 예정된 심사는 없습니다.")
    
    c1, c2 = st.columns(2)
    c1.warning("🌧️ [제주 날씨] 습도 높음! 안전 운행")
    c2.info("💡 차량 운행 시 창문 닫기 & 안전벨트 확인")

# [2] 차량 운행표
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 차량 스케줄")
    
    # 1. 운행 모드
    mode = st.radio("운행 모드", ["등원 (집 → 도장)", "하원 (도장 → 집)"], horizontal=True)
    
    # 2. 컬럼 설정
    if "등원" in mode:
        veh_col = '등원차량'
        time_col = '등원시간'
        loc_col = '등원장소'
    else:
        veh_col = '하원차량'
        time_col = '하원시간'
        loc_col = '하원장소'
        
    # 3. 데이터 필터링
    if not df_students.empty and veh_col in df_students.columns:
        
        # (1) 차량 배정된 아이들만
        target = df_students[df_students[veh_col].notna() & (df_students[veh_col] != '')]
        
        # (2) 이용여부 체크 ('O', '이용' 포함된 경우만)
        if '차량이용여부' in df_students.columns:
             target = target[target['차량이용여부'].fillna('').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]

        # 4. 차량 선택
        if not target.empty:
            # 차량 목록 정렬 (1호차, 2호차...)
            car_list = sorted(target[veh_col].unique().tolist())
            selected_car = st.selectbox("배차 선택", car_list)
            
            # 5. 최종 리스트 및 시간 정렬
            final_df = target[target[veh_col] == selected_car]
            
            if time_col in final_df.columns:
                final_df = final_df.sort_values(by=time_col, ascending=True, na_position='last')
            
            st.write(f"### 🕒 {selected_car} {mode} ({len(final_df)}명)")
            
            # 6. 표 출력
            cols_to_show = [time_col, '이름', loc_col, '수련부']
            cols_to_show = [c for c in cols_to_show if c in final_df.columns]
            
            # 체크박스를 위해 반복문 사용
            for i, row in final_df.iterrows():
                c1, c2, c3, c4 = st.columns([2, 2, 3, 1])
                c1.write(f"**{row[time_col]}**")
                c2.write(f"**{row['이름']}**")
                c3.write(f"{row[loc_col]}")
                c4.checkbox("탑승", key=f"car_{i}")
                
        else:
            st.info(f"운행 데이터가 없습니다. (엑셀 '{veh_col}' 확인)")
    else:
        st.error(f"엑셀에 '{veh_col}' 컬럼이 없습니다.")

# [3] 수련부 출석
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    if '수련부' in df_students.columns:
        class_list = sorted(df_students['수련부'].dropna().unique().tolist())
        if class_list:
            selected_class = st.selectbox("수련 시간 선택", class_list)
            class_students = df_students[df_students['수련부'] == selected_class]
            st.write(f"### 🥋 {selected_class} ({len(class_students)}명)")
            cols = st.columns(3)
            for i, row in class_students.iterrows():
                with cols[i % 3]:
                    st.checkbox(f"{row['이름']}", key=f"att_{i}")
        else:
            st.info("수련부 데이터가 없습니다.")
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
            g_type = row.get('기질유형', '미입력')
            st.success(f"**{name}** ({g_type})")
            if not df_guide.empty and '기질유형' in df_guide.columns:
                guide = df_guide[df_guide['기질유형'] == g_type]
                if not guide.empty:
                    g_row = guide.iloc[0]
                    st.info(f"특징: {g_row.get('핵심특징', '-')}")
                    st.warning(f"지도법: {g_row.get('지도_DO(해라)', '-')}")
        else:
            st.error("없는 이름입니다.")

# [5] 훈육 코치
elif menu == "💬 훈육 코치":
    st.header("💬 AI 훈육 코치")
    if not df_guide.empty:
        types = df_guide['기질유형'].unique()
        sel = st.selectbox("기질 선택", types)
        if st.button("솔루션 보기"):
            guide = df_guide[df_guide['기질유형'] == sel].iloc[0]
            st.code(guide.get('훈육_스크립트', '데이터 없음'))

# [6] 승급심사
elif menu == "📈 승급심사 관리":
    st.header("📈 승급심사 현황")
    if not df_students.empty and '심사일시' in df_students.columns:
        df_test = df_students[df_students['심사일시'].fillna('').str.strip() != '']
        if not df_test.empty:
            df_test = df_test.sort_values(by='심사일시')
            level_col = '단' if '단' in df_students.columns else '현재급'
            cols_to_show = ['심사일시', '이름', level_col, '수련부']
            cols_to_show = [c for c in cols_to_show if c in df_test.columns]
            st.dataframe(df_test[cols_to_show], use_container_width=True, hide_index=True)
        else:
            st.info("예정된 심사자가 없습니다.")

# [7] 이달의 생일
elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일자")
    this_month = datetime.now().month
    st.subheader(f"{this_month}월의 주인공 🎉")
    
    birth_col = '생일' if '생일' in df_students.columns else '생년월일'
    if not df_students.empty and birth_col in df_students.columns:
        df_students['temp_date'] = pd.to_datetime(df_students[birth_col], format='%Y%m%d', errors='coerce')
        if df_students['temp_date'].isna().all():
             df_students['temp_date'] = pd.to_datetime(df_students[birth_col], errors='coerce')
        
        b_kids = df_students[df_students['temp_date'].dt.month == this_month]
        if not b_kids.empty:
            st.balloons()
            for i, row in b_kids.iterrows():
                date_str = row['temp_date'].strftime('%m월 %d일') if pd.notnull(row['temp_date']) else str(row[birth_col])
                st.info(f"🎂 {row['이름']} ({date_str})")
        else:
            st.write("생일자가 없습니다.")
