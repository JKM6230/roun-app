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

# [디자인 강제 고정]
st.markdown("""
    <style>
        :root { color-scheme: light; }
        [data-testid="stAppViewContainer"], .stApp { background-color: #ffffff !important; }
        [data-testid="stSidebar"] { background-color: #f0f2f6 !important; }
        h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
        .stTextInput input { color: #000000 !important; }
        button { border: 1px solid #ddd !important; background-color: white !important; }
        .list-row { border-bottom: 1px solid #eee; padding: 10px 0; }
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

# [데이터 로드]
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
        
        if '상태' in df.columns:
            df = df[~df['상태'].str.contains('휴관|퇴원|중단|쉬는', case=False, na=False)]
            
        if '장기일정' in df.columns:
            today_str = get_korea_time().strftime("%Y-%m-%d")
            updates_made = False
            for i, row in df.iterrows():
                schedule = str(row.get('장기일정', '')).strip()
                current_status = str(row.get('출석확인', '')).strip()
                if schedule and "~" in schedule and ":" in schedule:
                    try:
                        dates, reason = schedule.split(":")
                        start_date, end_date = dates.split("~")
                        start_date = start_date.strip()
                        end_date = end_date.strip()
                        
                        if today_str > end_date:
                            cell = worksheet.find(row['이름'])
                            if cell:
                                target_col = worksheet.find("장기일정").col
                                worksheet.update_cell(cell.row, target_col, "")
                                updates_made = True
                        elif start_date <= today_str <= end_date:
                            if current_status == '':
                                cell = worksheet.find(row['이름'])
                                if cell:
                                    row_num = cell.row
                                    try:
                                        worksheet.update_cell(row_num, worksheet.find("출석확인").col, "결석")
                                        worksheet.update_cell(row_num, worksheet.find("비고").col, reason)
                                        try: worksheet.update_cell(row_num, worksheet.find("등원확인").col, "결석")
                                        except: pass
                                        try: worksheet.update_cell(row_num, worksheet.find("하원확인").col, "결석")
                                        except: pass
                                        updates_made = True
                                    except: pass
                    except: pass
            if updates_made:
                load_fast_data.clear()
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
                df = df.astype(str)
                if '상태' in df.columns:
                    df = df[~df['상태'].str.contains('휴관|퇴원|중단|쉬는', case=False, na=False)]
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

def load_consultation_logs(student_name):
    client = get_gspread_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("상담일지")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        target_df = df[df['이름'] == student_name]
        return target_df.iloc[::-1]
    except:
        return pd.DataFrame()

def add_consultation_log(student_name, content):
    client = get_gspread_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("상담일지")
        today = get_korea_time().strftime("%Y-%m-%d")
        ws.append_row([today, student_name, content])
        return True
    except:
        return False

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

def register_long_term_schedule(student_name, start_date, end_date, reason):
    client = get_gspread_client()
    if not client: return False
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        cell = worksheet.find(student_name)
        row_num = cell.row
        
        s_str = start_date.strftime("%Y-%m-%d")
        e_str = end_date.strftime("%Y-%m-%d")
        schedule_str = f"{s_str}~{e_str}:{reason}"
        
        target_col = worksheet.find("장기일정").col
        worksheet.update_cell(row_num, target_col, schedule_str)
        
        today_str = get_korea_time().strftime("%Y-%m-%d")
        if s_str <= today_str <= e_str:
            try:
                worksheet.update_cell(row_num, worksheet.find("출석확인").col, "결석")
                worksheet.update_cell(row_num, worksheet.find("비고").col, reason)
                worksheet.update_cell(row_num, worksheet.find("등원확인").col, "결석")
                worksheet.update_cell(row_num, worksheet.find("하원확인").col, "결석")
            except: pass
            
        load_fast_data.clear()
        return True
    except: return False

def archive_daily_attendance():
    client = get_gspread_client()
    if not client: return False, "서버 연결 실패"
    
    try:
        sh = client.open_by_key(SHEET_ID)
        ws_daily = sh.worksheet("원생명단")
        try: ws_monthly = sh.worksheet("월간출석부")
        except: return False, "'월간출석부' 시트가 없습니다."

        daily_data = ws_daily.get_all_records()
        if not daily_data: return False, "데이터가 없습니다."
        df_daily = pd.DataFrame(daily_data)
        
        names = df_daily['이름'].tolist()
        name_col_data = [['이름']] + [[n] for n in names]
        ws_monthly.update(range_name=f"A1:A{len(name_col_data)}", values=name_col_data)
        
        today_str = get_korea_time().strftime("%m/%d")
        log_column = [today_str]
        
        for idx, row in df_daily.iterrows():
            status = row.get('출석확인', '')
            note = str(row.get('비고', '')).strip()
            if status == '출석': mark = 'O'
            elif note and note != 'nan': mark = note
            elif status == '결석': mark = 'X'
            else: mark = ''
            log_column.append(mark)
            
        header_row = ws_monthly.row_values(1)
        next_col_idx = len(header_row) + 1
        col_letter = gspread.utils.rowcol_to_a1(1, next_col_idx).replace('1', '')
        range_str = f"{col_letter}1:{col_letter}{len(log_column)}"
        ws_monthly.update(range_name=range_str, values=[[val] for val in log_column])
        
        return True, f"{today_str} 저장 완료!"
    except Exception as e:
        return False, f"오류: {e}"

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
    st.markdown("**System Ver 64.0 (Notice Color)**")
    st.write("---")
    auto_refresh = st.toggle("실시간 모드 (10초)", value=False)
    if auto_refresh:
        st.caption("⚡ 10초마다 갱신 중...")
        time.sleep(10)
        st.rerun()
    menu = st.radio("메뉴 선택", ["🏠 홈 대시보드", "🚍 차량 운행표", "📝 수련부 출석", "📞 학부모 상담", "📉 오늘의 결석자", "🧠 기질/훈육 통합", "📈 승급심사 관리", "🎂 이달의 생일", "🔐 관리자 모드"])
    st.markdown("---")
    if st.button("🔄 데이터 전체 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 1. 홈 (공지사항 컬러 적용)
if menu == "🏠 홈 대시보드":
    now = get_korea_time()
    weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    st.markdown(f"<div style='text-align: right; font-size: 1.5em; font-weight: bold; margin-bottom: 20px;'>📅 {now.strftime('%m월 %d일')} {weekdays[now.weekday()]}</div>", unsafe_allow_html=True)
    st.header("📢 오늘의 작전 브리핑")
    
    if not df_notice.empty and len(df_notice.columns) >= 2:
        recent_notices = df_notice.tail(10)
        for i, row in recent_notices.iloc[::-1].iterrows():
            content = str(row.iloc[1]).strip()
            if not content: continue
            
            # [NEW] 공지사항 컬러링 로직
            # 기본값: 초록색 (기타)
            bg_color = "#e8f5e9" # 연한 초록
            border_color = "#4caf50" # 진한 초록
            icon = "✅"
            
            # 키워드 감지
            if "[상담]" in content:
                bg_color = "#ffebee" # 연한 빨강
                border_color = "#ef5350" # 진한 빨강
                icon = "📞"
            elif "[도복]" in content:
                bg_color = "#e3f2fd" # 연한 파랑
                border_color = "#2196f3" # 진한 파랑
                icon = "🥋"
            elif "[심사]" in content or "심사" in content:
                bg_color = "#fff9c4" # 연한 노랑
                border_color = "#fbc02d" # 진한 노랑
                icon = "🏆"
                
            # HTML 카드 출력
            st.markdown(f"""
            <div style="
                background-color: {bg_color};
                border-left: 5px solid {border_color};
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
                color: black;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            ">
                <div style="font-weight:bold; font-size:1.05em; margin-bottom:5px;">{icon} 공지</div>
                <div style="white-space: pre-wrap;">{content}</div>
            </div>
            """, unsafe_allow_html=True)
            
    else: st.info("등록된 공지사항이 없습니다.")
    
    st.markdown("---")
    if not df_schedule.empty:
        today_test = df_schedule[pd.to_datetime(df_schedule.iloc[:,0].astype(str).str.replace('.','-'), errors='coerce').dt.date == now.date()]
        if not today_test.empty:
            st.error(f"🔥 **오늘 승급심사: {len(today_test)}명**")
            for i, row in today_test.iterrows(): st.write(f" - {row.iloc[1]}")
        else: st.success("✅ 오늘 예정된 심사는 없습니다.")

# 2. 차량
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 통합 운행표")
    now = get_korea_time()
    today_char = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    st.caption(f"📅 **오늘({today_char}요일)** 기준 리스트")
    if not df_students.empty:
        working_df = df_students.copy()
        for col in ['등원차량', '등원시간', '등원장소', '하원차량', '하원시간', '하원장소']:
            if col in working_df.columns: working_df[col] = working_df[col].apply(lambda x: parse_schedule_for_today(x, today_char))
        if '차량이용여부' in working_df.columns: working_df = working_df[working_df['차량이용여부'].fillna('O').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]
        
        all_cars = sorted(list(set([x for x in working_df['등원차량'].unique().tolist() + working_df['하원차량'].unique().tolist() if x and str(x).strip() != ''])))
        if all_cars:
            selected_car = st.selectbox("배차 선택", all_cars)
            schedule_list = []
            for mode, v_col, t_col, l_col, c_col in [('등원', '등원차량', '등원시간', '등원장소', '등원확인'), ('하원', '하원차량', '하원시간', '하원장소', '하원확인')]:
                for _, row in working_df[working_df[v_col] == selected_car].iterrows():
                    schedule_list.append({'name': row['이름'], 'type': mode, 'time': row.get(t_col, ''), 'loc': row.get(l_col, ''), 'status': row.get(c_col, ''), 'check_col': c_col})
            schedule_list.sort(key=lambda x: x['time'].strip() if x['time'] else "99:99")
            
            total = len(schedule_list)
            done = len([x for x in schedule_list if x['status'] in ['탑승', '결석']])
            st.progress(done/total if total > 0 else 0)
            
            curr_time = None
            for idx, item in enumerate(schedule_list):
                if item['time'] != curr_time:
                    st.markdown("---")
                    st.subheader(f"⏰ {item['time'] or '시간 미정'}")
                    curr_time = item['time']
                
                bg, border, icon = ("#e3f2fd", "#2196f3", "🟦") if item['type'] == '등원' else ("#fff9c4", "#fbc02d", "🟨")
                if item['status'] == '결석':
                    bg, border = "#ffebee", "#ef5350"
                
                status_html = ""
                if item['status'] == '탑승': status_html = "<span style='color:green;font-weight:bold;margin-left:10px;'>✅ 탑승완료</span>"
                elif item['status'] == '결석': status_html = "<span style='color:red;font-weight:bold;margin-left:10px;'>❌ 결석</span>"
                
                st.markdown(f"<div style='background-color:{bg};padding:15px;border-left:6px solid {border};border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);margin-bottom:5px;color:black !important;'><div style='font-size:1.2rem;font-weight:bold;color:black;margin-bottom:5px;'>{icon} {item['name']} ({item['type']})</div><div style='font-size:1rem;color:#333;'>📍 {item['loc']} {status_html}</div></div>", unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                key_base = f"{idx}_{item['name']}_{item['type']}"
                with c1:
                    if item['status'] == '탑승':
                        if st.button("취소", key=f"u_{key_base}"): update_check_status(item['name'], item['check_col'], ''); st.rerun()
                    else:
                        if st.button("탑승", key=f"r_{key_base}"): update_check_status(item['name'], item['check_col'], '탑승'); st.rerun()
                with c2:
                    if item['status'] == '결석':
                        if st.button("복구", key=f"ua_{key_base}"): update_check_status(item['name'], item['check_col'], ''); st.rerun()
                    else:
                        if st.button("결석", key=f"a_{key_base}"): update_check_status(item['name'], item['check_col'], '결석'); st.rerun()
                st.write("")
        else: st.info("운행 차량 없음")
    else: st.error("데이터 로드 실패")

# 3. 출석부
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    if '수련부' in df_students.columns:
        class_list = sorted([str(x) for x in df_students['수련부'].dropna().unique() if str(x).strip() != ''])
        if class_list:
            now = get_korea_time()
            today_char = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
            
            c1, c2 = st.columns([1, 2])
            with c1: show_today = st.toggle(f"📅 오늘({today_char})만", value=True)
            with c2: selected_class = st.selectbox("수련 시간", class_list)
            
            target = df_students[df_students['수련부'].astype(str) == selected_class]
            if show_today and '등원요일' in df_students.columns:
                target = target[target['등원요일'].astype(str).str.strip().eq('') | target['등원요일'].astype(str).str.contains(today_char)]
            
            st.write(f"### 🥋 {selected_class} ({len(target)}명)")
            st.caption("※ 초록색=출석 / 빨간색=결석 / 흰색=미체크")
            
            for i, row in target.sort_values('이름').iterrows():
                status = row.get('출석확인', '')
                note = row.get('비고', '')
                is_checked = (status == '출석')
                
                if status == '출석': card_bg, card_border, status_badge = "#e8f5e9", "#4caf50", "✅ 출석완료"
                elif status == '결석': card_bg, card_border, status_badge = "#ffebee", "#ef5350", "❌ 결석처리"
                else: card_bg, card_border, status_badge = "#ffffff", "#dddddd", ""

                bus_in = parse_schedule_for_today(row.get('등원차량', ''), today_char)
                bus_out = parse_schedule_for_today(row.get('하원차량', ''), today_char)
                bus_txt = f"🚌 {bus_in} " if bus_in else ""
                bus_txt += f"🏠 {bus_out}" if bus_out else ""
                if not bus_txt: bus_txt = "도보/자차"
                
                note_html = f"<div style='margin-top:5px;padding:5px;background:#fff3cd;border-radius:4px;font-size:0.9em;'>📌 {note}</div>" if note and str(note) != 'nan' else ""
                
                st.markdown(f"""
                <div style="background-color:{card_bg};border-left:5px solid {card_border};padding:12px;border-radius:5px;margin-top:15px;margin-bottom:5px;box-shadow:0 1px 3px rgba(0,0,0,0.1);color:black !important;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:1.3em;font-weight:bold;">{row['이름']}</span>
                        <span style="font-weight:bold;">{status_badge}</span>
                    </div>
                    <div style="font-size:0.9em;margin-top:5px;color:#555;">{bus_txt}</div>
                    {note_html}
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.checkbox("출석확인", value=is_checked, key=f"att_{i}_{row['이름']}"):
                        if not is_checked: update_check_status(row['이름'], "출석확인", '출석'); st.rerun()
                    else:
                        if is_checked: update_check_status(row['이름'], "출석확인", ''); st.rerun()
                with c2:
                    if status == '결석':
                        if st.button("결석취소", key=f"cncl_{i}"): update_check_status(row['이름'], "출석확인", ''); st.rerun()
                    else:
                        if st.button("결석처리", key=f"abs_{i}"): update_check_status(row['이름'], "출석확인", '결석'); st.rerun()
                
                with st.expander("🔽 특이사항 / 장기 일정 등록"):
                    t1, t2, t3, t4 = st.columns(4)
                    if t1.button("병결", key=f"s_{i}"): update_check_status(row['이름'], "비고", "병결"); st.rerun()
                    if t2.button("여행", key=f"t_{i}"): update_check_status(row['이름'], "비고", "여행"); st.rerun()
                    if t3.button("부상", key=f"h_{i}"): update_check_status(row['이름'], "비고", "부상"); st.rerun()
                    if t4.button("지움", key=f"d_{i}"): update_check_status(row['이름'], "비고", ""); st.rerun()
                    
                    safe_note = note if str(note) != 'nan' else ""
                    new_note = st.text_input("사유 직접 입력", value=safe_note, key=f"n_{i}")
                    if new_note != safe_note: update_check_status(row['이름'], "비고", new_note); st.rerun()
                    
                    st.markdown("---")
                    st.caption("📅 장기 일정 (자동결석)")
                    d1, d2, d3 = st.columns([2,2,1])
                    s_d = d1.date_input("시작", key=f"sd_{i}", value=datetime.now())
                    e_d = d2.date_input("종료", key=f"ed_{i}", value=datetime.now())
                    r_l = st.text_input("사유", key=f"rl_{i}")
                    if d3.button("저장", key=f"sl_{i}"):
                        if register_long_term_schedule(row['이름'], s_d, e_d, r_l): st.success("저장됨"); time.sleep(1); st.rerun()
                        else: st.error("실패")

# 4. 상담 로그
elif menu == "📞 학부모 상담":
    st.header("📞 학부모 상담 로그")
    search_name_input = st.text_input("원생 이름 입력", placeholder="예: 김지안 (입력 후 엔터)")
    if search_name_input:
        if search_name_input in df_students['이름'].values:
            search_name = search_name_input
            with st.container(border=True):
                st.subheader(f"📝 {search_name} 상담 기록 작성")
                new_log = st.text_area("상담 내용", height=100)
                if st.button("기록 저장"):
                    if new_log:
                        if add_consultation_log(search_name, new_log): st.success("저장되었습니다."); time.sleep(1); st.rerun()
                        else: st.error("실패")
                    else: st.warning("내용 입력 필요")
            st.markdown("---")
            st.subheader(f"🗂️ {search_name} 히스토리")
            logs = load_consultation_logs(search_name)
            if not logs.empty:
                for idx, row in logs.iterrows():
                    with st.chat_message("user"):
                        st.write(f"**{row['날짜']}**")
                        st.write(row['내용'])
            else: st.info("기록 없음")
        else: st.error(f"'{search_name_input}' 원생을 찾을 수 없습니다.")
    else: st.info("이름을 입력하면 상담 기록이 나타납니다.")

# 5. 결석자
elif menu == "📉 오늘의 결석자":
    st.header("📉 오늘의 결석 현황")
    if '출석확인' in df_students.columns:
        absent = df_students[df_students['출석확인'] == '결석']
        st.metric("총 결석", f"{len(absent)}명")
        if not absent.empty: st.dataframe(absent[['이름', '수련부', '비고'] if '비고' in absent.columns else ['이름', '수련부']], hide_index=True, use_container_width=True)
        else: st.success("결석자 없음 🎉")

# 6. 기질/훈육
elif menu == "🧠 기질/훈육 통합":
    st.header("🧠 훈육 가이드")
    name = st.text_input("이름 검색")
    if name:
        res = df_students[df_students['이름'] == name]
        if not res.empty:
            row = res.iloc[0]
            gtype = row.get('기질유형', '미검사')
            st.subheader(f"{name} ({gtype})")
            if gtype != '미검사' and not df_guide.empty:
                guide = df_guide[df_guide['기질유형'] == gtype]
                if not guide.empty:
                    gr = guide.iloc[0]
                    st.info(f"DO: {gr.get('지도_DO(해라)', '-')}"); st.warning(f"DON'T: {gr.get('지도_DONT(하지마라)', '-')}")
                    with st.expander("스크립트"): st.text(gr.get('훈육_스크립트', ''))
        else: st.error("없음")

# 7. 승급심사
elif menu == "📈 승급심사 관리":
    st.header("📈 승급심사")
    if not df_schedule.empty: st.dataframe(df_schedule, hide_index=True, use_container_width=True)

# 8. 생일
elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일")
    # (생략)

# 9. 관리자
elif menu == "🔐 관리자 모드":
    st.header("관리자")
    if st.text_input("PW", type="password") == "0577":
        st.success("승인됨")
        st.warning("⚠️ 하루 마감 시 '월간출석부'에 기록되고 초기화됩니다.")
        if st.button("🔥 마감 및 저장"):
            with st.spinner("저장 중..."):
                ok, msg = archive_daily_attendance()
            if ok:
                st.success(msg)
                with st.spinner("초기화 중..."):
                    try:
                        c = get_gspread_client()
                        ws = c.open_by_key(SHEET_ID).worksheet("원생명단")
                        ranges = []
                        for col in ["등원확인", "하원확인", "출석확인", "비고"]:
                            try:
                                l = gspread.utils.rowcol_to_a1(1, ws.find(col).col).replace('1', '')
                                ranges.append(f"{l}2:{l}1000")
                            except: pass
                        if ranges: ws.batch_clear(ranges); st.success("완료! 👋"); load_fast_data.clear(); time.sleep(2); st.rerun()
                    except: st.error("초기화 실패")
            else: st.error(msg)
