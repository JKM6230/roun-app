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
        df = df.astype(str) # 모든 데이터를 문자로 변환
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

# [핵심] 데이터 쓰기 함수 (연동 로직)
def update_check_status(student_name, col_name, status_value):
    client = get_gspread_client()
    if not client: return

    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        
        try:
            cell = worksheet.find(student_name)
            row_num = cell.row
            
            # 연동 로직
            cols_to_update = []
            if col_name == "출석확인":
                if status_value == "결석":
                    cols_to_update = ["출석확인", "등원확인", "하원확인"]
                elif status_value == "":
                    cols_to_update = ["출석확인", "등원확인", "하원확인"]
                else:
                    cols_to_update = ["출석확인"]
            else:
                cols_to_update = [col_name]

            for target_col in cols_to_update:
                try:
                    header_cell = worksheet.find(target_col)
                    col_num = header_cell.col
                    worksheet.update_cell(row_num, col_num, status_value)
                    time.sleep(0.5) 
                except:
                    pass
            
            load_fast_data.clear() 
            
        except gspread.exceptions.APIError as e:
            pass
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
    st.markdown("**System Ver 35.0 (Safety)**")
    
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
        "🧠 기질/훈육 통합",
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

# [2] 차량 운행표
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
            
            for i, row in final_df.iterrows():
                current_status = row.get(check_col, '')
                
                if current_status == '탑승':
                    box = st.success
                elif current_status == '결석':
                    box = st.error
                else:
                    box = None
                
                def draw_content():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    t_val = row[time_col] if time_col in row else "-"
                    l_val = row[loc_col] if loc_col in row else "-"
                    with c1:
                        st.markdown(f"#### ⏰ {t_val} | {row['이름']}")
                        st.markdown(f"📍 {l_val}")
                    with c2:
                        if current_status == '탑승':
                            if st.button("✅ 완료", key=f"btn_b_{row['이름']}_{mode}"):
                                update_check_status(row['이름'], check_col, '')
                                st.rerun()
                        else:
                            if st.button("탑승", key=f"btn_b_{row['이름']}_{mode}"):
                                update_check_status(row['이름'], check_col, '탑승')
                                st.rerun()
                    with c3:
                        if current_status == '결석':
                            if st.button("❌ 완료", key=f"btn_a_{row['이름']}_{mode}"):
                                update_check_status(row['이름'], check_col, '')
                                st.rerun()
                        else:
                            if st.button("결석", key=f"btn_a_{row['이름']}_{mode}"):
                                update_check_status(row['이름'], check_col, '결석')
                                st.rerun()
                
                if box:
                    with box(f"{current_status} 처리됨"):
                        draw_content()
                else:
                    with st.container(border=True):
                        draw_content()

        else:
            st.info("해당 차량에 탑승하는 인원이 없습니다.")
    else:
        st.error("데이터 로드 실패")

# [3] 수련부 출석 (안전 모드 적용)
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    
    # 1. 컬럼 존재 확인
    if '수련부' in df_students.columns:
        try:
            # 2. 수련부 목록 안전하게 가져오기 (문자열 변환 후 정렬)
            raw_classes = df_students['수련부'].dropna().unique()
            class_list = sorted([str(x) for x in raw_classes if str(x).strip() != ''])
            
            if class_list:
                selected_class = st.selectbox("수련 시간 선택", class_list)
                
                # 3. 학생 필터링
                class_students = df_students[df_students['수련부'].astype(str) == selected_class].sort_values(by='이름')
                
                st.write(f"### 🥋 {selected_class} ({len(class_students)}명)")
                st.caption("※ '결석' 버튼을 누르면 차량 스케줄도 '결석' 처리됩니다.")
                
                check_col = "출석확인"
                note_col = "비고"
                
                # 4. 카드 그리기 (반복문)
                for i, row in class_students.iterrows():
                    current_val = row.get(check_col, '')
                    current_note = row.get(note_col, '')
                    
                    # 박스 타입 결정
                    if current_val == '출석':
                        box_type = st.success
                        msg = "✅ 출석 완료"
                    elif current_val == '결석':
                        box_type = st.error
                        msg = "❌ 결석 (차량 연동됨)"
                    else:
                        box_type = None
                        msg = ""
                    
                    # 내부 콘텐츠 함수 (오류 방지를 위해 함수 대신 직접 구현도 고려 가능하나, 가독성을 위해 유지)
                    def draw_att_card():
                        c1, c2, c3 = st.columns([2, 1, 1])
                        with c1:
                            st.subheader(f"{row['이름']}")
                            if current_note and str(current_note).lower() != 'nan':
                                st.caption(f"📝 {current_note}")
                        with c2:
                            if current_val == '출석':
                                if st.button("✅ 완료", key=f"p_c_{i}_{row['이름']}"):
                                    update_check_status(row['이름'], check_col, '')
                                    st.rerun()
                            else:
                                if st.button("출석", key=f"p_{i}_{row['이름']}"):
                                    update_check_status(row['이름'], check_col, '출석')
                                    st.rerun()
                        with c3:
                            if current_val == '결석':
                                if st.button("❌ 완료", key=f"a_c_{i}_{row['이름']}"):
                                    update_check_status(row['이름'], check_col, '')
                                    st.rerun()
                            else:
