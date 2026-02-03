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
gid_attendance = "244532436"  # 출석부
gid_schedule = "538477435"    # 심사일정

# ==========================================
# 1. 데이터 로드 엔진
# ==========================================
st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

if 'check_status' not in st.session_state:
    st.session_state['check_status'] = {}

@st.cache_data(ttl=0)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

df_students = load_data(gid_students)
df_notice = load_data(gid_notice)
df_guide = load_data(gid_guide)
df_schedule = load_data(gid_schedule)

# ==========================================
# 2. 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    st.markdown("**System Ver 14.0 (Fix)**")
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
    
    # [일반용] 데이터만 새로고침 (체크박스 유지)
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("---")

    # [관리자용] 완전 초기화 (체크박스 삭제)
    st.markdown("### 🔐 관리자 메뉴")
    admin_pw = st.text_input("비밀번호 입력", type="password", key="admin_pw")
    
    if admin_pw == "0577":
        if st.button("🔥 하루 시작 (완전 초기화)"):
            st.session_state['check_status'] = {} 
            st.cache_data.clear()
            st.rerun()
        st.success("관리자 인증됨")

# ==========================================
# 3. 기능 구현
# ==========================================

# [1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    st.header("📢 오늘의 작전 브리핑")
    st.caption("최근 등록된 공지사항 3개가 표시됩니다.")
    
    if not df_notice.empty:
        try:
            recent_notices = df_notice.tail(3)
            for i, row in recent_notices.iloc[::-1].iterrows():
                n_date = row[0] if pd.notna(row[0]) else "-"
                n_content = row[1] if pd.notna(row[1]) else ""
                if n_content.strip():
                    st.info(f"**[{n_date}]** {n_content}")
        except:
            st.warning("공지사항 데이터 오류")
    else:
        st.info("등록된 공지사항이 없습니다.")

    st.markdown("---")
    
    # [수정됨] 심사 일정 날짜 인식 강화
    today_dt = datetime.now().date()
    
    if not df_schedule.empty:
        date_col = '날짜' if '날짜' in df_schedule.columns else df_schedule.columns[0]
        
        # 1. 날짜 정제 (공백 제거 및 숫자/하이픈만 남기기)
        # 예: "2026. 2. 4" -> "202624" (X) -> 좀 더 안전하게 to_datetime에 맡기되 공백제거
        df_schedule['clean_date'] = df_schedule[date_col].astype(str).str.replace(' ', '').str.replace('.', '-')
        
        # 2. 날짜 객체로 변환
        df_schedule['smart_date'] = pd.to_datetime(df_schedule['clean_date'], errors='coerce').dt.date
        
        # 3. 오늘 날짜와 비교
        today_test = df_schedule[df_schedule['smart_date'] == today_dt]
        
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows():
                name_val = row['이름'] if '이름' in row else row.iloc[1]
                st.write(f" - **{name_val}** (화이팅!)")
        else:
            st.success("✅ 오늘 예정된 심사는 없습니다.")
    else:
        st.info("심사 일정 데이터가 없습니다.")

# [2] 차량 운행표
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 차량 스케줄")
    
    mode = st.radio("운행 모드", ["등원 (집 → 도장)", "하원 (도장 → 집)"], horizontal=True)
    
    if "등원" in mode:
        veh_col = '등원차량'
        time_col = '등원시간'
        loc_col = '등원장소'
        mode_key = "in"
    else:
        veh_col = '하원차량'
        time_col = '하원시간'
        loc_col = '하원장소'
        mode_key = "out"

    if not df_students.empty:
        if veh_col in df_students.columns:
            target = df_students[df_students[veh_col].notna() & (df_students[veh_col] != '')]
            
            if '차량이용여부' in df_students.columns:
                target = target[target['차량이용여부'].fillna('O').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]
            
            if not target.empty:
                car_list = sorted(target[veh_col].unique().tolist())
                selected_car = st.selectbox("배차 선택", car_list)
                
                final_df = target[target[veh_col] == selected_car]
                
                if time_col in final_df.columns:
                    final_df = final_df.sort_values(by=time_col, ascending=True, na_position='last')
                
                st.write(f"### 🕒 {selected_car} {mode} ({len(final_df)}명)")
                
                for i, row in final_df.iterrows():
                    c1, c2, c3, c4 = st.columns([2, 2, 3, 1])
                    t_val = row[time_col] if time_col in row else "-"
                    l_val = row[loc_col] if loc_col in row else "-"
                    
                    c1.write(f"**{t_val}**")
                    c2.write(f"**{row['이름']}**")
                    c3.write(f"{l_val}")
                    
                    unique_id = f"car_{selected_car}_{mode_key}_{row['이름']}"
                    saved_val = st.session_state['check_status'].get(unique_id, False)
                    is_checked = c4.checkbox("확인", value=saved_val, key=unique_id)
                    st.session_state['check_status'][unique_id] = is_checked
            else:
                st.info(f"조건에 맞는 탑승 인원이 없습니다.")
        else:
            st.error(f"🚨 엑셀에 **'{veh_col}'** 이라는 제목이 없습니다.")
    else:
        st.error("데이터를 불러오지 못했습니다.")

# [3] 수련부 출석
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    if '수련부' in df_students.columns:
        class_list = sorted(df_students['수련부'].dropna().unique().tolist())
        if class_list:
            selected_class = st.selectbox("수련 시간 선택", class_list)
            class_students = df_students[df_students['수련부'] == selected_class].sort_values(by='이름')
            
            st.write(f"### 🥋 {selected_class} ({len(class_students)}명)")
            cols = st.columns(3)
            
            for i, row in class_students.iterrows():
                with cols[i % 3]:
                    unique_id = f"att_{selected_class}_{row['이름']}"
                    saved_val = st.session_state['check_status'].get(unique_id, False)
                    is_checked = st.checkbox(f"{row['이름']}", value=saved_val, key=unique_id)
                    st.session_state['check_status'][unique_id] = is_checked
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
    st.info("※ [심사일정] 탭의 데이터를 보여줍니다.")
    
    if not df_schedule.empty:
        target_df = df_schedule.copy()
        date_col = '날짜' if '날짜' in target_df.columns else target_df.columns[0]
        
        # 스마트 정렬 (날짜로 인식)
        target_df['clean_date'] = target_df[date_col].astype(str).str.replace(' ', '').str.replace('.', '-')
        target_df['sort_date'] = pd.to_datetime(target_df['clean_date'], errors='coerce')
        target_df = target_df.sort_values(by='sort_date')
        
        st.dataframe(target_df.drop(columns=['clean_date', 'sort_date'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.warning("등록된 심사 일정이 없습니다.")

# [7] 이달의 생일 (일 기준 정렬)
elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일자")
    this_month = datetime.now().month
    st.subheader(f"{this_month}월의 주인공 🎉")
    
    birth_col = '생일' if '생일' in df_students.columns else '생년월일'
    if not df_students.empty and birth_col in df_students.columns:
        df_students['clean_birth'] = df_students[birth_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df_students['temp_date'] = pd.to_datetime(df_students['clean_birth'], format='%Y%m%d', errors='coerce')
        
        b_kids = df_students[df_students['temp_date'].dt.month == this_month]
        
        if not b_kids.empty:
            # [수정됨] 일(Day)만 뽑아서 정렬 (연도 무시)
            b_kids['day_only'] = b_kids['temp_date'].dt.day
            b_kids = b_kids.sort_values(by='day_only')
            
            st.balloons()
            for i, row in b_kids.iterrows():
                d_str = row['temp_date'].strftime('%m월 %d일') if pd.notnull(row['temp_date']) else str(row[birth_col])
                info_txt = f"🎂 **{row['이름']}** ({d_str})"
                if '수련부' in row: info_txt += f" - {row['수련부']}"
                st.info(info_txt)
        else:
            st.write(f"{this_month}월 생일자가 없습니다.")
    else:
        st.error(f"엑셀에 '{birth_col}' 컬럼이 없습니다.")
