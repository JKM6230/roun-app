import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

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

def get_korea_time():
    return datetime.utcnow() + timedelta(hours=9)

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
    st.markdown("**System Ver 19.0 (Admin & Absent)**")
    st.markdown("---")
    
    # [변경됨] 통합 조회를 관리자 모드로 숨김
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚍 차량 운행표", 
        "📝 수련부 출석", 
        "🔍 기질 인사이트", 
        "💬 훈육 코치", 
        "📈 승급심사 관리",
        "🎂 이달의 생일",
        "🔐 관리자 모드" # [NEW] 맨 아래로 이동
    ])
    
    st.markdown("---")
    
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 기능 구현
# ==========================================

# [1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    # 실시간 시계
    st.markdown(
        """
        <div style="text-align: right; font-size: 1.2em; font-weight: bold; color: #444; margin-bottom: 10px;">
            🕒 현재 시간: <span id="clock"></span>
        </div>
        <script>
        function startTime() {
            const today = new Date();
            let h = today.getHours();
            let m = today.getMinutes();
            let s = today.getSeconds();
            m = checkTime(m);
            s = checkTime(s);
            document.getElementById('clock').innerHTML =  h + ":" + m + ":" + s;
            setTimeout(startTime, 1000);
        }
        function checkTime(i) {
            if (i < 10) {i = "0" + i};
            return i;
        }
        startTime();
        </script>
        """,
        unsafe_allow_html=True
    )

    st.header("📢 오늘의 작전 브리핑")
    
    # 공지사항
    if not df_notice.empty:
        try:
            recent_notices = df_notice.tail(10)
            weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
            
            for i, row in recent_notices.iloc[::-1].iterrows():
                n_date_raw = row[0] if pd.notna(row[0]) else "-"
                n_content = row[1] if pd.notna(row[1]) else ""
                
                display_date = n_date_raw
                try:
                    dt_obj = pd.to_datetime(str(n_date_raw).replace('.', '-'), errors='coerce')
                    if pd.notnull(dt_obj):
                        w_str = weekdays[dt_obj.weekday()]
                        display_date = f"{dt_obj.strftime('%m/%d')} {w_str}"
                except:
                    pass

                if n_content.strip():
                    st.info(f"**[{display_date}]** {n_content}")
        except:
            st.warning("공지사항 데이터 오류")
    else:
        st.info("등록된 공지사항이 없습니다.")

    st.markdown("---")
    
    # 심사 일정
    today_dt = get_korea_time().date()
    
    if not df_schedule.empty:
        date_col = '날짜' if '날짜' in df_schedule.columns else df_schedule.columns[0]
        df_schedule['clean_date'] = df_schedule[date_col].astype(str).str.replace(' ', '').str.replace('.', '-')
        df_schedule['smart_date'] = pd.to_datetime(df_schedule['clean_date'], errors='coerce').dt.date
        
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
        
    # 오늘 생일자
    birth_col = '생일' if '생일' in df_students.columns else '생년월일'
    if not df_students.empty and birth_col in df_students.columns:
        df_students['clean_birth'] = df_students[birth_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df_students['temp_date'] = pd.to_datetime(df_students['clean_birth'], format='%Y%m%d', errors='coerce')
        
        today_birth = df_students[
            (df_students['temp_date'].dt.month == today_dt.month) & 
            (df_students['temp_date'].dt.day == today_dt.day)
        ]
        
        if not today_birth.empty:
            st.markdown("---")
            st.subheader("🎂 오늘 생일 축하합니다!")
            for i, row in today_birth.iterrows():
                st.warning(f"🎉 **{row['이름']}**")

# [NEW] 관리자 모드 (통합조회 + 초기화)
elif menu == "🔐 관리자 모드":
    st.header("🔐 관리자 전용 모드")
    
    # 비밀번호 입력
    admin_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if admin_pw == "0577":
        st.success("관리자 권한이 승인되었습니다.")
        st.markdown("---")
        
        # 탭 분리
        tab1, tab2 = st.tabs(["🔍 원생 통합 조회", "🔥 시스템 관리"])
        
        with tab1:
            st.subheader("원생 정보 조회")
            search_name = st.text_input("이름 검색 (예: 김지안)", placeholder="이름을 입력하세요")
            
            if search_name and not df_students.empty:
                student = df_students[df_students['이름'] == search_name]
                if not student.empty:
                    s_data = student.iloc[0]
                    level = s_data.get('단', s_data.get('현재급', '-'))
                    cls_time = s_data.get('수련부', '-')
                    g_type = s_data.get('기질유형', '미검사')
                    phone_1 = s_data.get('보호자연락처', '-')
                    phone_2 = s_data.get('기타보호자연락처', '-')
                    in_car = s_data.get('등원차량', '-')
                    in_time = s_data.get('등원시간', '-')
                    in_loc = s_data.get('등원장소', '-')
                    out_car = s_data.get('하원차량', '-')
                    out_time = s_data.get('하원시간', '-')
                    out_loc = s_data.get('하원장소', '-')

                    st.markdown("---")
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.subheader(f"🥋 {s_data['이름']}")
                        st.write(f"**수련부:** {cls_time}")
                        st.write(f"**현재급:** {level}")
                        st.info(f"**기질:** {g_type}")
                    with c2:
                        st.subheader("📞 비상 연락망")
                        st.write(f"**보호자:** {phone_1}")
                        st.write(f"**기타:** {phone_2}")
                    
                    st.markdown("---")
                    st.subheader("🚍 차량 이용 정보")
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        st.write("🔵 **등원**")
                        st.write(f"- {in_car} / {in_time}")
                        st.write(f"- {in_loc}")
                    with tc2:
                        st.write("🟠 **하원**")
                        st.write(f"- {out_car} / {out_time}")
                        st.write(f"- {out_loc}")
                        
                    if not df_guide.empty and g_type != '미검사':
                        st.markdown("---")
                        guide_match = df_guide[df_guide['기질유형'] == g_type]
                        if not guide_match.empty:
                            g_row = guide_match.iloc[0]
                            with st.expander(f"💡 {g_type} 지도 가이드 보기"):
                                st.write(f"**특징:** {g_row.get('핵심특징', '-')}")
                                st.write(f"**지도법:** {g_row.get('지도_DO(해라)', '-')}")
                else:
                    st.error("검색된 원생이 없습니다.")
        
        with tab2:
            st.subheader("데이터 초기화")
            st.warning("경고: 이 버튼을 누르면 모든 체크 상태가 사라집니다.")
            if st.button("🔥 하루 시작 (모든 체크 삭제)"):
                st.session_state['check_status'] = {} 
                st.cache_data.clear()
                st.rerun()
                
    elif admin_pw:
        st.error("비밀번호가 틀렸습니다.")

# [2] 차량 운행표 (결석 체크 추가)
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
                
                # 진행률 계산 (탑승만 계산)
                total_count = len(final_df)
                checked_count = 0
                for _, row in final_df.iterrows():
                    unique_id = f"car_{selected_car}_{mode_key}_{row['이름']}"
                    if st.session_state['check_status'].get(unique_id, False):
                        checked_count += 1
                
                progress_val = checked_count / total_count if total_count > 0 else 0
                
                st.write(f"### 🕒 {selected_car} {mode}")
                st.progress(progress_val)
                st.caption(f"🏁 **탑승 현황: {checked_count} / {total_count} 명 ({int(progress_val * 100)}%)**")
                
                st.markdown("---")

                # 카드 뷰 출력 (결석 체크 추가)
                for i, row in final_df.iterrows():
                    with st.container(border=True):
                        # 3단 분리: 정보(6) | 탑승(2) | 결석(2)
                        c1, c2, c3 = st.columns([3, 1, 1])
                        
                        t_val = row[time_col] if time_col in row else "-"
                        l_val = row[loc_col] if loc_col in row else "-"
                        
                        with c1:
                            st.markdown(f"#### ⏰ {t_val} | {row['이름']}")
                            st.markdown(f"📍 {l_val}")
                            
                        with c2:
                            unique_id = f"car_{selected_car}_{mode_key}_{row['이름']}"
                            saved_val = st.session_state['check_status'].get(unique_id, False)
                            st.write("") 
                            # 탑승 체크
                            is_checked = st.checkbox("✅ 탑승", value=saved_val, key=unique_id)
                            if is_checked != saved_val:
                                st.session_state['check_status'][unique_id] = is_checked
                                st.rerun()

                        with c3:
                            # 결석 체크
                            absent_id = f"absent_{selected_car}_{mode_key}_{row['이름']}"
                            absent_val = st.session_state['check_status'].get(absent_id, False)
                            st.write("")
                            # 결석 체크
                            is_absent = st.checkbox("❌ 결석", value=absent_val, key=absent_id)
                            if is_absent != absent_val:
                                st.session_state['check_status'][absent_id] = is_absent
                                # 결석은 굳이 리런할 필요 없으나 데이터 저장을 위해 session 사용
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
                    
                    if is_checked != saved_val:
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
        
        target_df['clean_date'] = target_df[date_col].astype(str).str.replace(' ', '').str.replace('.', '-')
        target_df['sort_date'] = pd.to_datetime(target_df['clean_date'], errors='coerce')
        target_df = target_df.sort_values(by='sort_date')
        
        st.dataframe(target_df.drop(columns=['clean_date', 'sort_date'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.warning("등록된 심사 일정이 없습니다.")

# [7] 이달의 생일
elif menu == "🎂 이달의 생일":
    kst_now = get_korea_time()
    this_month = kst_now.month
    
    st.header("🎂 이달의 생일자")
    st.subheader(f"{this_month}월의 주인공 🎉")
    
    birth_col = '생일' if '생일' in df_students.columns else '생년월일'
    if not df_students.empty and birth_col in df_students.columns:
        df_students['clean_birth'] = df_students[birth_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df_students['temp_date'] = pd.to_datetime(df_students['clean_birth'], format='%Y%m%d', errors='coerce')
        
        b_kids = df_students[df_students['temp_date'].dt.month == this_month]
        
        if not b_kids.empty:
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
