import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time

# ==========================================
# [설정] 구글 시트 연동
# ==========================================
SHEET_ID = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

def get_korea_time():
    return datetime.utcnow() + timedelta(hours=9)

@st.cache_resource
def get_gspread_client():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        return None

# [최적화 1] 자주 바뀌는 데이터 (5초 캐시)
@st.cache_data(ttl=5) 
def load_fast_data():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df = df.astype(str)
        return df
    except:
        return pd.DataFrame()

# [최적화 2] 잘 안 바뀌는 데이터 (10분 캐시)
@st.cache_data(ttl=600)
def load_slow_data(sheet_name):
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        if len(rows) < 2: return pd.DataFrame() 
        headers = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)
        return df
    except:
        return pd.DataFrame()

# 데이터 쓰기 함수
def update_check_status(student_name, col_name, status_value):
    client = get_gspread_client()
    if not client: return

    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        
        try:
            cell = worksheet.find(student_name)
            row_num = cell.row
            header_cell = worksheet.find(col_name)
            col_num = header_cell.col
            
            worksheet.update_cell(row_num, col_num, status_value)
            load_fast_data.clear() 
            
        except gspread.exceptions.APIError as e:
            if "429" in str(e):
                time.sleep(2)
                worksheet.update_cell(row_num, col_num, status_value)
                load_fast_data.clear()
        except Exception as e:
            pass 
    except:
        pass

# 데이터 로드
df_students = load_fast_data() 
df_notice = load_slow_data("공지사항")
df_guide = load_slow_data("기질가이드")
df_schedule = load_slow_data("심사일정")

# ==========================================
# 2. 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    st.markdown("**System Ver 30.0 (Fixed)**")
    
    st.write("---")
    st.write("#### 📡 연결 상태")
    
    auto_refresh = st.toggle("실시간 모드 (10초)", value=False)
    if auto_refresh:
        st.caption("⚡ 10초마다 갱신 중...")
        time.sleep(10)
        st.rerun()
        
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚍 차량 운행표", 
        "📝 수련부 출석", 
        "🔍 기질 인사이트", 
        "💬 훈육 코치", 
        "📈 승급심사 관리",
        "🎂 이달의 생일",
        "🔐 관리자 모드"
    ])
    
    st.markdown("---")
    if st.button("🔄 데이터 전체 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 3. 기능 구현
# ==========================================

# [1] 홈 대시보드
if menu == "🏠 홈 대시보드":
    now = get_korea_time()
    weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    date_str = now.strftime("%m월 %d일")
    day_str = weekdays[now.weekday()]
    
    st.markdown(
        f"""
        <div style="text-align: right; font-size: 1.5em; font-weight: bold; color: #555; margin-bottom: 20px;">
            📅 {date_str} {day_str}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header("📢 오늘의 작전 브리핑")
    
    if auto_refresh:
        st.caption("🟢 실시간 업데이트 중...")

    if not df_notice.empty and len(df_notice.columns) >= 2:
        recent_notices = df_notice.tail(10)
        for i, row in recent_notices.iloc[::-1].iterrows():
            raw_date = str(row.iloc[0]).strip()
            content = str(row.iloc[1]).strip()
            
            if not content: continue
            
            display_date = raw_date
            try:
                dt_obj = pd.to_datetime(raw_date.replace('.', '-'), errors='coerce')
                if pd.notnull(dt_obj):
                    w_str = weekdays[dt_obj.weekday()]
                    display_date = f"{dt_obj.strftime('%m/%d')} {w_str}"
            except:
                pass 
            st.info(f"**[{display_date}]** {content}")
            
    else:
        st.info("등록된 공지사항이 없거나 불러오지 못했습니다.")

    st.markdown("---")
    
    today_dt = get_korea_time().date()
    
    if not df_schedule.empty:
        date_col = df_schedule.columns[0]
        name_col = df_schedule.columns[1] if len(df_schedule.columns) > 1 else df_schedule.columns[0]
        
        df_schedule['clean_date'] = df_schedule[date_col].astype(str).str.replace(' ', '').str.replace('.', '-')
        df_schedule['smart_date'] = pd.to_datetime(df_schedule['clean_date'], errors='coerce').dt.date
        
        today_test = df_schedule[df_schedule['smart_date'] == today_dt]
        
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows():
                st.write(f" - **{row[name_col]}** (화이팅!)")
        else:
            st.success("✅ 오늘 예정된 심사는 없습니다.")
            
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

# [관리자 모드]
elif menu == "🔐 관리자 모드":
    st.header("🔐 관리자 전용 모드")
    admin_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if admin_pw == "0577":
        st.success("관리자 권한이 승인되었습니다.")
        st.markdown("---")
        
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
                    in_car = s_data.get('등원차량', '-')
                    in_time = s_data.get('등원시간', '-')
                    
                    st.markdown(f"### 🥋 {s_data['이름']}")
                    st.write(f"**정보:** {level} | {cls_time}부 | {g_type}")
                    st.write(f"**연락처:** {phone_1}")
                    st.write(f"**차량:** 등원({in_car}/{in_time})")

                else:
                    st.error("검색된 원생이 없습니다.")
        
        with tab2:
            st.subheader("데이터 초기화")
            st.warning("⚠️ 하루 일과가 끝나면 눌러주세요. (등원/하원/출석 기록을 모두 지웁니다)")
            if st.button("🔥 하루 마감 (전체 삭제)"):
                with st.spinner("구글 시트 청소 중..."):
                    try:
                        client = get_gspread_client()
                        sh = client.open_by_key(SHEET_ID)
                        ws = sh.worksheet("원생명단")
                        
                        cols_to_clear = ["등원확인", "하원확인", "출석확인"]
                        ranges = []
                        
                        for c_name in cols_to_clear:
                            try:
                                cell = ws.find(c_name)
                                col_letter = gspread.utils.rowcol_to_a1(1, cell.col).replace('1', '')
                                ranges.append(f"{col_letter}2:{col_letter}1000")
                            except:
                                pass
                        
                        if ranges:
                            ws.batch_clear(ranges)
                            st.success("모든 체크 기록이 초기화되었습니다.")
                            load_fast_data.clear()
                            st.rerun()
                        else:
                            st.error("초기화할 컬럼을 찾지 못했습니다.")
                    except Exception as e:
                        st.error(f"오류 발생: {e}")
                
    elif admin_pw:
        st.error("비밀번호가 틀렸습니다.")

# [2] 차량 운행표 (수정됨)
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 차량 스케줄")
    
    mode = st.radio("운행 모드", ["등원 (집 → 도장)", "하원 (도장 → 집)"], horizontal=True)
    
    if "등원" in mode:
        veh_col = '등원차량'
        time_col = '등원시간'
        loc_col = '등원장소'
        check_col = '등원확인'
    else:
        veh_col = '하원차량'
        time_col = '하원시간'
        loc_col = '하원장소'
        check_col = '하원확인'

    if not df_students.empty and veh_col in df_students.columns:
        target = df_students[df_students[veh_col].notna() & (df_students[veh_col] != '')]
        if '차량이용여부' in df_students.columns:
            target = target[target['차량이용여부'].fillna('O').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]
        
        if not target.empty:
            car_list = sorted(target[veh_col].unique().tolist())
            selected_car = st.selectbox("배차 선택", car_list)
            
            final_df = target[target[veh_col] == selected_car]
            
            if time_col in final_df.columns:
                final_df = final_df.sort_values(by=time_col, ascending=True, na_position='last')
            
            # 진행률 계산
            total_count = len(final_df)
            boarded_count = 0
            absent_count = 0
            
            if check_col in final_df.columns:
                boarded_count = len(final_df[final_df[check_col] == '탑승'])
                absent_count = len(final_df[final_df[check_col] == '결석'])
            
            processed_count = boarded_count + absent_count
            progress_val = processed_count / total_count if total_count > 0 else 0
            
            st.write(f"### 🕒 {selected_car} {mode}")
            st.progress(progress_val)
            
            st.markdown(f"""
            <div style='background-color:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:15px;'>
                <b>📊 총원: {total_count}명</b> | 
                <span style='color:blue'>✅ 탑승: {boarded_count}</span> | 
                <span style='color:red'>❌ 결석: {absent_count}</span> | 
                <span style='color:gray'>⏳ 미확인: {total_count - processed_count}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # [핵심] 에러 안 나는 안전한 카드 그리기 함수
            def draw_card(row, status):
                c1, c2, c3 = st.columns([3, 1, 1])
                t_val = row[time_col] if time_col in row else "-"
                l_val = row[loc_col] if loc_col in row else "-"
                
                with c1:
                    st.markdown(f"#### ⏰ {t_val} | {row['이름']}")
                    st.markdown(f"📍 {l_val}")
                with c2:
                    if status == '탑승':
                        if st.button("✅ 완료", key=f"btn_b_{row['이름']}_{mode}"):
                            update_check_status(row['이름'], check_col, '')
                            st.rerun()
                    else:
                        if st.button("탑승", key=f"btn_b_{row['이름']}_{mode}"):
                            update_check_status(row['이름'], check_col, '탑승')
                            st.rerun()
                with c3:
                    if status == '결석':
                            if st.button("❌ 완료", key=f"btn_a_{row['이름']}_{mode}"):
                                update_check_status(row['이름'], check_col, '')
                                st.rerun()
                    else:
                        if st.button("결석", key=f"btn_a_{row['이름']}_{mode}"):
                            update_check_status(row['이름'], check_col, '결석')
                            st.rerun()

            # 상태별 박스 분기 (에러 방지: if-else 명확화)
            for i, row in final_df.iterrows():
                current_status = row.get(check_col, '')
                
                if current_status == '탑승':
                    with st.success(f"✅ 탑승 확인 완료"):
                        draw_card(row, current_status)
                elif current_status == '결석':
                    with st.error(f"❌ 결석 처리됨"):
                        draw_card(row, current_status)
                else:
                    with st.container(border=True):
                        draw_card(row, current_status)

        else:
            st.info("해당 차량에 탑승하는 인원이 없습니다.")
    else:
        st.error("데이터 로드 실패")

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
            
            check_col = "출석확인"
            
            for i, row in class_students.iterrows():
                with cols[i % 3]:
                    current_val = row.get(check_col, '')
                    is_checked = (current_val == '출석')
                    
                    new_check = st.checkbox(f"{row['이름']}", value=is_checked, key=f"att_{selected_class}_{i}_{row['이름']}")
                    
                    if new_check != is_checked:
                        new_status = '출석' if new_check else ''
                        update_check_status(row['이름'], check_col, new_status)
                        st.rerun()
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
