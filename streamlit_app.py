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

# [디자인 강제 고정 - HTML 카드 방식]
st.markdown("""
    <style>
        :root { color-scheme: light; }
        [data-testid="stAppViewContainer"], .stApp { background-color: #ffffff !important; }
        [data-testid="stSidebar"] { background-color: #f0f2f6 !important; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
        .stTextInput input { color: #000000 !important; }
        button { border: 1px solid #ddd !important; background-color: white !important; }
    </style>
""", unsafe_allow_html=True)

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
        cell = worksheet.find(student_name)
        row_num = cell.row
        
        cols_to_update = []
        if col_name == "출석확인":
            if status_value == "결석" or status_value == "":
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
    except:
        pass

# [NEW] 월간 출석부 저장 함수
def archive_daily_attendance():
    client = get_gspread_client()
    if not client: return False, "서버 연결 실패"
    
    try:
        sh = client.open_by_key(SHEET_ID)
        ws_daily = sh.worksheet("원생명단")
        
        # 월간출석부 시트 없으면 생성 시도 (혹은 에러)
        try:
            ws_monthly = sh.worksheet("월간출석부")
        except:
            return False, "'월간출석부' 시트가 없습니다. 엑셀에 시트를 추가해주세요."

        # 1. 오늘의 데이터 가져오기
        daily_data = ws_daily.get_all_records()
        if not daily_data: return False, "데이터가 없습니다."
        
        df_daily = pd.DataFrame(daily_data)
        
        # 2. 이름 순서 동기화 (원생명단의 이름 순서대로 월간출석부 A열 업데이트)
        names = df_daily['이름'].tolist()
        
        # A열(이름) 업데이트 - 1행은 헤더('이름') 유지
        name_col_data = [['이름']] + [[n] for n in names]
        ws_monthly.update(range_name=f"A1:A{len(name_col_data)}", values=name_col_data)
        
        # 3. 오늘 날짜 및 출석 상태 리스트 생성
        today_str = get_korea_time().strftime("%m/%d")
        
        # 기록할 데이터: [날짜] + [각 학생의 상태]
        log_column = [today_str]
        
        for idx, row in df_daily.iterrows():
            status = row.get('출석확인', '')
            if status == '출석':
                mark = 'O'
            elif status == '결석':
                mark = 'X'
            else:
                mark = '' # 미출석/결석 아님
            log_column.append(mark)
            
        # 4. 빈 컬럼 찾아서 쓰기
        # 1행(헤더)을 읽어서 비어있는 첫 번째 컬럼 찾기
        header_row = ws_monthly.row_values(1)
        next_col_idx = len(header_row) + 1
        
        # gspread에서 컬럼 번호를 A1 표기법으로 변환하지 않고 cell update 사용이 느리므로
        # 범위 업데이트 사용. (예: B1:B50)
        col_letter = gspread.utils.rowcol_to_a1(1, next_col_idx) # A1, B1 ...
        col_letter = col_letter.replace('1', '') # A, B ...
        
        range_str = f"{col_letter}1:{col_letter}{len(log_column)}"
        
        # 데이터 형태 변환 (리스트 -> 리스트의 리스트 [[val], [val]])
        update_values = [[val] for val in log_column]
        
        ws_monthly.update(range_name=range_str, values=update_values)
        
        return True, f"{today_str} 출석 기록 저장 완료!"
        
    except Exception as e:
        return False, f"오류 발생: {e}"

def parse_schedule_for_today(raw_text, today_char):
    raw_text = str(raw_text).strip()
    if not raw_text: return ""
    if "(" not in raw_text: return raw_text
    settings = raw_text.split(',')
    for setting in settings:
        if "(" in setting and ")" in setting:
            parts = setting.split('(')
            val = parts[0].strip()
            days = parts[1].replace(')', '').strip()
            if today_char in days: return val
    return ""

df_students = load_fast_data() 
df_notice = load_slow_data("공지사항")
df_guide = load_slow_data("기질가이드")
df_schedule = load_slow_data("심사일정")

# ==========================================
# UI 시작
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    st.markdown("**System Ver 54.0 (Archive)**")
    
    st.write("---")
    auto_refresh = st.toggle("실시간 모드 (10초)", value=False)
    if auto_refresh:
        st.caption("⚡ 10초마다 갱신 중...")
        time.sleep(10)
        st.rerun()
        
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚍 차량 운행표", 
        "📝 수련부 출석", 
        "📉 오늘의 결석자", 
        "🧠 기질/훈육 통합", 
        "📈 승급심사 관리",
        "🎂 이달의 생일",
        "🔐 관리자 모드"
    ])
    
    st.markdown("---")
    if st.button("🔄 데이터 전체 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 1. 홈 대시보드
if menu == "🏠 홈 대시보드":
    now = get_korea_time()
    weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    date_str = now.strftime("%m월 %d일")
    day_str = weekdays[now.weekday()]
    
    st.markdown(f"<div style='text-align: right; font-size: 1.5em; font-weight: bold; margin-bottom: 20px;'>📅 {date_str} {day_str}</div>", unsafe_allow_html=True)
    st.header("📢 오늘의 작전 브리핑")
    
    if not df_notice.empty and len(df_notice.columns) >= 2:
        recent_notices = df_notice.tail(10)
        for i, row in recent_notices.iloc[::-1].iterrows():
            content = str(row.iloc[1]).strip()
            if not content: continue
            st.info(f"**[공지]** {content}")
    else:
        st.info("등록된 공지사항이 없습니다.")

    st.markdown("---")
    today_dt = get_korea_time().date()
    if not df_schedule.empty:
        today_test = df_schedule[pd.to_datetime(df_schedule.iloc[:,0].astype(str).str.replace('.','-'), errors='coerce').dt.date == today_dt]
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows():
                st.write(f" - {row.iloc[1]}")
        else:
            st.success("✅ 오늘 예정된 심사는 없습니다.")

# 2. 차량 운행표
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 통합 운행표")
    now = get_korea_time()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    today_char = weekdays_kr[now.weekday()]
    st.caption(f"📅 **오늘({today_char}요일)** 기준 리스트")

    if not df_students.empty:
        working_df = df_students.copy()
        for col in ['등원차량', '등원시간', '등원장소', '하원차량', '하원시간', '하원장소']:
            if col in working_df.columns:
                working_df[col] = working_df[col].apply(lambda x: parse_schedule_for_today(x, today_char))
        
        if '차량이용여부' in working_df.columns:
            working_df = working_df[working_df['차량이용여부'].fillna('O').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]

        cars_in = working_df['등원차량'].unique().tolist()
        cars_out = working_df['하원차량'].unique().tolist()
        all_cars = sorted(list(set([x for x in cars_in + cars_out if x and str(x).strip() != ''])))
        
        if all_cars:
            selected_car = st.selectbox("배차 선택", all_cars)
            schedule_list = []
            for mode, v_col, t_col, l_col, c_col in [('등원', '등원차량', '등원시간', '등원장소', '등원확인'), ('하원', '하원차량', '하원시간', '하원장소', '하원확인')]:
                temp_df = working_df[working_df[v_col] == selected_car]
                for _, row in temp_df.iterrows():
                    schedule_list.append({
                        'name': row['이름'], 'type': mode, 'time': row.get(t_col, ''), 'loc': row.get(l_col, ''), 'status': row.get(c_col, ''), 'check_col': c_col
                    })
            
            schedule_list.sort(key=lambda x: x['time'].strip() if x['time'] else "99:99")
            
            total_cnt = len(schedule_list)
            done_cnt = len([x for x in schedule_list if x['status'] in ['탑승', '결석']])
            st.progress(done_cnt / total_cnt if total_cnt > 0 else 0)
            
            current_time_group = None
            for idx, item in enumerate(schedule_list):
                time_display = item['time'] if item['time'] else "시간 미정"
                if time_display != current_time_group:
                    st.markdown("---")
                    st.subheader(f"⏰ {time_display}")
                    current_time_group = time_display
                
                if item['type'] == '등원':
                    bg_color, border_color, icon = "#e3f2fd", "#2196f3", "🟦"
                else:
                    bg_color, border_color, icon = "#fff9c4", "#fbc02d", "🟨"
                
                is_done = (item['status'] == '탑승')
                is_absent = (item['status'] == '결석')
                
                status_html = ""
                if is_done: status_html = "<span style='color:green; font-weight:bold; margin-left:10px;'>✅ 탑승완료</span>"
                if is_absent: status_html = "<span style='color:red; font-weight:bold; margin-left:10px;'>❌ 결석</span>"

                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 15px; border-left: 6px solid {border_color}; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 5px; color: black !important;">
                    <div style="font-size: 1.2rem; font-weight: bold; color: black; margin-bottom: 5px;">
                        {icon} {item['name']} ({item['type']})
                    </div>
                    <div style="font-size: 1rem; color: #333;">
                        📍 {item['loc']} {status_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if is_done:
                        if st.button("취소", key=f"u_{idx}_{item['name']}_{item['type']}"):
                            update_check_status(item['name'], item['check_col'], '')
                            st.rerun()
                    else:
                        if st.button("탑승", key=f"r_{idx}_{item['name']}_{item['type']}"):
                            update_check_status(item['name'], item['check_col'], '탑승')
                            st.rerun()
                with c2:
                    if is_absent:
                        if st.button("복구", key=f"ua_{idx}_{item['name']}_{item['type']}"):
                            update_check_status(item['name'], item['check_col'], '')
                            st.rerun()
                    else:
                        if st.button("결석", key=f"a_{idx}_{item['name']}_{item['type']}"):
                            update_check_status(item['name'], item['check_col'], '결석')
                            st.rerun()
                st.write("") 
        else:
            st.info("오늘 운행하는 차량이 없습니다.")
    else:
        st.error("데이터 로드 실패")

# 3. 수련부 출석
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    if '수련부' in df_students.columns:
        class_list = sorted([str(x) for x in df_students['수련부'].dropna().unique() if str(x).strip() != ''])
        
        if class_list:
            now = get_korea_time()
            weekdays = ["월", "화", "수", "목", "금", "토", "일"]
            today_char = weekdays[now.weekday()]
            
            c_filter, c_select = st.columns([1, 2])
            with c_filter:
                show_today_only = st.toggle(f"📅 오늘({today_char})만", value=True)
            with c_select:
                selected_class = st.selectbox("수련 시간 선택", class_list)
            
            class_students = df_students[df_students['수련부'].astype(str) == selected_class]
            
            if show_today_only and '등원요일' in df_students.columns:
                class_students = class_students[
                    (class_students['등원요일'].astype(str).str.strip() == '') | 
                    (class_students['등원요일'].astype(str).str.contains(today_char))
                ]
            
            class_students = class_students.sort_values(by='이름')
            
            st.write(f"### 🥋 {selected_class} ({len(class_students)}명)")
            st.caption("※ 카드가 초록색이면 출석, 빨간색이면 결석입니다.")
            
            check_col = "출석확인"
            note_col = "비고"
            
            for i, row in class_students.iterrows():
                current_val = row.get(check_col, '')
                current_note = row.get(note_col, '')
                is_checked = (current_val == '출석')
                
                if current_val == '출석':
                    card_bg, card_border, status_badge = "#e8f5e9", "#4caf50", "✅ 출석완료"
                elif current_val == '결석':
                    card_bg, card_border, status_badge = "#ffebee", "#ef5350", "❌ 결석처리"
                else:
                    card_bg, card_border, status_badge = "#ffffff", "#dddddd", ""

                bus_in = parse_schedule_for_today(row.get('등원차량', ''), today_char)
                bus_out = parse_schedule_for_today(row.get('하원차량', ''), today_char)
                
                bus_html = ""
                if bus_in: bus_html += f"<span style='color:#555; margin-right:10px;'>🚌 {bus_in}</span>"
                if bus_out: bus_html += f"<span style='color:#555;'>🏠 {bus_out}</span>"
                if not bus_html: bus_html = "<span style='color:#999;'>도보/자차</span>"

                note_html = ""
                if current_note and str(current_note) != 'nan':
                    note_html = f"<div style='margin-top:5px; padding:5px; background:#fff3cd; border-radius:4px; font-size:0.9em;'>📌 {current_note}</div>"

                st.markdown(f"""
                <div style="background-color: {card_bg}; border-left: 5px solid {card_border}; padding: 12px; border-radius: 5px; margin-top: 15px; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.3em; font-weight:bold; color:black;">{row['이름']}</span>
                        <span style="font-weight:bold; color:black;">{status_badge}</span>
                    </div>
                    <div style="font-size:0.9em; margin-top:5px;">{bus_html}</div>
                    {note_html}
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.checkbox("출석확인", value=is_checked, key=f"att_{i}_{row['이름']}"):
                        if not is_checked:
                            update_check_status(row['이름'], check_col, '출석')
                            st.rerun()
                    else:
                        if is_checked:
                            update_check_status(row['이름'], check_col, '')
                            st.rerun()
                with c2:
                    if current_val == '결석':
                        if st.button("결석취소", key=f"cncl_{i}"):
                            update_check_status(row['이름'], check_col, '')
                            st.rerun()
                    else:
                        if st.button("결석처리", key=f"abs_{i}"):
                            update_check_status(row['이름'], check_col, '결석')
                            st.rerun()

                with st.expander("특이사항 / 사유 입력"):
                    cols = st.columns(4)
                    if cols[0].button("병결", key=f"s_{i}"):
                        update_check_status(row['이름'], note_col, "병결")
                        st.rerun()
                    if cols[1].button("여행", key=f"t_{i}"):
                        update_check_status(row['이름'], note_col, "여행")
                        st.rerun()
                    if cols[2].button("부상", key=f"h_{i}"):
                        update_check_status(row['이름'], note_col, "부상")
                        st.rerun()
                    if cols[3].button("지움", key=f"d_{i}"):
                        update_check_status(row['이름'], note_col, "")
                        st.rerun()
                    
                    safe_note = current_note if str(current_note) != 'nan' else ""
                    new_note = st.text_input("직접 입력", value=safe_note, key=f"n_{i}")
                    if new_note != safe_note:
                        update_check_status(row['이름'], note_col, new_note)
                        st.rerun()
        else:
            st.info("수련부 데이터가 없습니다.")
    else:
        st.error("엑셀에 '수련부' 컬럼이 없습니다.")

# 4. 오늘의 결석자
elif menu == "📉 오늘의 결석자":
    st.header("📉 오늘의 결석 현황")
    if '출석확인' in df_students.columns:
        absent = df_students[df_students['출석확인'] == '결석']
        st.metric("총 결석", f"{len(absent)}명")
        if not absent.empty:
            cols = ['이름', '수련부', '비고'] if '비고' in absent.columns else ['이름', '수련부']
            st.dataframe(absent[cols], hide_index=True, use_container_width=True)
        else:
            st.success("결석자가 없습니다! 🎉")

# 5. 기질/훈육
elif menu == "🧠 기질/훈육 통합":
    st.header("🧠 원생 맞춤형 훈육 가이드")
    name = st.text_input("원생 이름 검색")
    if name:
        target = df_students[df_students['이름'] == name]
        if not target.empty:
            row = target.iloc[0]
            gtype = row.get('기질유형', '미검사')
            st.subheader(f"{name} ({gtype})")
            if gtype != '미검사' and not df_guide.empty:
                guide = df_guide[df_guide['기질유형'] == gtype]
                if not guide.empty:
                    gr = guide.iloc[0]
                    st.info(f"**DO:** {gr.get('지도_DO(해라)', '-')}")
                    st.warning(f"**DON'T:** {gr.get('지도_DONT(하지마라)', '-')}")
                    with st.expander("훈육 스크립트"):
                        st.text(gr.get('훈육_스크립트', ''))
        else:
            st.error("원생을 찾을 수 없습니다.")

# 6. 승급심사/생일/관리자
elif menu == "📈 승급심사 관리":
    st.header("📈 승급심사 현황")
    if not df_schedule.empty:
        st.dataframe(df_schedule, hide_index=True, use_container_width=True)

elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일")
    # (생일 로직 동일)

elif menu == "🔐 관리자 모드":
    st.header("🔐 관리자 전용 모드")
    admin_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if admin_pw == "0577":
        st.success("관리자 권한이 승인되었습니다.")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🔍 원생 통합 조회", "🔥 시스템 관리"])
        
        with tab1:
            st.write("(통합 조회 기능)")
            
        with tab2:
            st.subheader("하루 마감 (출석부 저장 및 초기화)")
            st.warning("⚠️ 주의: 이 버튼을 누르면 오늘의 출석 기록이 '월간출석부'로 넘어가고, 현재 화면은 초기화됩니다.")
            
            if st.button("🔥 마감 및 저장하기"):
                with st.spinner("1. 월간 출석부 기록 중..."):
                    success, msg = archive_daily_attendance()
                
                if success:
                    st.success(msg)
                    time.sleep(1)
                    with st.spinner("2. 데이터 초기화 중..."):
                        try:
                            client = get_gspread_client()
                            sh = client.open_by_key(SHEET_ID)
                            ws = sh.worksheet("원생명단")
                            # 초기화할 컬럼들
                            cols_to_clear = ["등원확인", "하원확인", "출석확인", "비고"]
                            ranges = []
                            for c_name in cols_to_clear:
                                try:
                                    cell = ws.find(c_name)
                                    col_letter = gspread.utils.rowcol_to_a1(1, cell.col).replace('1', '')
                                    ranges.append(f"{col_letter}2:{col_letter}1000")
                                except: pass
                            if ranges:
                                ws.batch_clear(ranges)
                                st.success("✅ 모든 데이터가 초기화되었습니다. 퇴근하셔도 좋습니다! 👋")
                                load_fast_data.clear()
                                time.sleep(2)
                                st.rerun()
                        except Exception as e:
                            st.error(f"초기화 실패: {e}")
                else:
                    st.error(f"저장 실패: {msg}")
    elif admin_pw:
        st.error("비밀번호가 틀렸습니다.")
