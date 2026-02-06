import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import google.generativeai as genai
import tempfile
import os
import importlib.metadata

# ==========================================
# [설정] 구글 시트 ID & API KEY
# ==========================================
SHEET_ID = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"
GEMINI_API_KEY = "AIzaSyDJCGd0w3NzpXfxoPYR-Ka8cNgtfxSjbIE"

st.set_page_config(page_title="로운태권도 통합 관제실", page_icon="🥋", layout="wide")

# [스타일]
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
        st.error(f"❌ 인증 오류: {e}")
        return None

# ==========================================
# [데이터 로드 함수]
# ==========================================
@st.cache_data(ttl=5) 
def load_fast_data():
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        rows = worksheet.get_all_values()
        if len(rows) < 2: return pd.DataFrame()
        headers = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=headers)
        df = df.loc[:, ~df.columns.str.match(r'^\s*$')]
        if '상태' in df.columns:
            df = df[~df['상태'].str.contains('휴관|퇴원|중단|쉬는', case=False, na=False)]
        
        if '장기일정' in df.columns:
            today_str = get_korea_time().strftime("%Y-%m-%d")
            for i, row in df.iterrows():
                schedule = str(row.get('장기일정', '')).strip()
                current_status = str(row.get('출석확인', '')).strip()
                if schedule and "~" in schedule and ":" in schedule:
                    try:
                        dates, reason = schedule.split(":")
                        start_date, end_date = dates.split("~")
                        if start_date.strip() <= today_str <= end_date.strip():
                            if current_status == '':
                                cell = worksheet.find(row['이름'])
                                if cell:
                                    worksheet.update_cell(cell.row, worksheet.find("출석확인").col, "결석")
                                    worksheet.update_cell(cell.row, worksheet.find("비고").col, reason)
                                    time.sleep(0.5)
                                    load_fast_data.clear()
                                    return load_fast_data()
                    except: pass
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_slow_data(sheet_name):
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        if len(rows) < 2: return pd.DataFrame() 
        return pd.DataFrame(rows[1:], columns=rows[0])
    except: return pd.DataFrame()

def get_alliance_athletes():
    client = get_gspread_client()
    if not client: return []
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("선수단기록")
        names_col = ws.col_values(2)
        if len(names_col) < 2: return []
        unique_names = sorted(list(set([n for n in names_col[1:] if n.strip()])))
        return unique_names
    except: return []

def register_new_alliance_player(name, team, note):
    client = get_gspread_client()
    if not client: return False
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("선수단기록")
        today = get_korea_time().strftime("%Y-%m-%d")
        ws.append_row([today, name, team, "선수등록", 0, 0, 0, 0, 0, "등록", 0, note, ""])
        return True
    except: return False

def load_consultation_logs(student_name):
    client = get_gspread_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("상담일지")
        rows = ws.get_all_values()
        if len(rows) < 2: return pd.DataFrame()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        return df[df['이름'] == student_name].iloc[::-1]
    except: return pd.DataFrame()

def add_consultation_log(student_name, content):
    client = get_gspread_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("상담일지")
        ws.append_row([get_korea_time().strftime("%Y-%m-%d"), student_name, content])
        return True
    except: return False

def update_check_status(student_name, col_name, status_value):
    client = get_gspread_client()
    if not client: return
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        cell = worksheet.find(student_name)
        cols = ["출석확인", "등원확인", "하원확인"] if col_name == "출석확인" and status_value in ["결석", ""] else [col_name]
        headers = worksheet.row_values(1)
        for c in cols:
            if c in headers:
                worksheet.update_cell(cell.row, headers.index(c) + 1, status_value)
                time.sleep(0.5)
        load_fast_data.clear() 
    except: pass

def register_long_term_schedule(student_name, start_date, end_date, reason):
    client = get_gspread_client()
    if not client: return False
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.worksheet("원생명단")
        cell = ws.find(student_name)
        s_str, e_str = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        headers = ws.row_values(1)
        if "장기일정" in headers:
            ws.update_cell(cell.row, headers.index("장기일정")+1, f"{s_str}~{e_str}:{reason}")
        load_fast_data.clear()
        return True
    except: return False

def archive_daily_attendance():
    client = get_gspread_client()
    if not client: return False, "연결 실패"
    try:
        sh = client.open_by_key(SHEET_ID)
        ws_daily = sh.worksheet("원생명단")
        ws_monthly = sh.worksheet("월간출석부")
        daily_data = ws_daily.get_all_values()
        if len(daily_data) < 2: return False, "데이터 없음"
        df = pd.DataFrame(daily_data[1:], columns=daily_data[0])
        today_str = get_korea_time().strftime("%m/%d")
        names = [['이름']] + [[n] for n in df['이름'].tolist()]
        ws_monthly.update(range_name=f"A1:A{len(names)}", values=names)
        log_col = [today_str]
        for _, row in df.iterrows():
            stat = row.get('출석확인', '')
            note = str(row.get('비고', '')).strip()
            if stat == '출석': mark = 'O'
            elif note: mark = note
            elif stat == '결석': mark = 'X'
            else: mark = ''
            log_col.append(mark)
        header = ws_monthly.row_values(1)
        col_letter = gspread.utils.rowcol_to_a1(1, len(header)+1).replace('1', '')
        ws_monthly.update(range_name=f"{col_letter}1:{col_letter}{len(log_col)}", values=[[v] for v in log_col])
        return True, "마감 완료"
    except Exception as e: return False, str(e)

def parse_schedule_for_today(raw, day_char):
    if "(" not in str(raw): return str(raw)
    for s in str(raw).split(','):
        if "(" in s and ")" in s:
            p = s.split('(')
            if day_char in p[1]: return p[0].strip()
    return ""

# ==========================================
# [데이터 로드 실행]
# ==========================================
df_students = load_fast_data()
df_notice = load_slow_data("공지사항")
df_guide = load_slow_data("기질가이드")
df_schedule = load_slow_data("심사일정")

# ==========================================
# [사이드바]
# ==========================================
with st.sidebar:
    st.title("🥋 로운태권도")
    
    # [라이브러리 버전 확인]
    try:
        ver = importlib.metadata.version("google-generativeai")
        st.caption(f"📚 Lib Ver: {ver}")
    except: st.caption("Library not found")

    st.write("---")
    
    # [AI 자동 연결]
    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except Exception as e:
            st.error(f"키 설정 오류: {e}")

    # [★ AI 진단 버튼]
    with st.expander("🔑 AI 연결 테스트 (클릭)", expanded=True):
        if st.button("내 키로 사용 가능한 모델 조회"):
            try:
                models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        models.append(m.name)
                
                if models:
                    st.success("✅ 연결 성공! 사용 가능 모델:")
                    st.code(models)
                else:
                    st.error("❌ 연결은 됐지만 사용 가능한 모델이 없습니다.")
            except Exception as e:
                st.error(f"❌ 연결 실패: {e}")
                st.info("API 키가 정확한지, 구글 AI Studio에서 'Generative Language API'가 활성화되었는지 확인하세요.")

    auto_refresh = st.toggle("실시간 모드 (10초)", value=False)
    if auto_refresh:
        time.sleep(10)
        st.rerun()

    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", "🚍 차량 운행표", "📝 수련부 출석", 
        "🏆 정권연합선수반", "📞 학부모 상담", "📉 오늘의 결석자", 
        "🧠 기질/훈육 통합", "📈 승급심사 관리", "🎂 이달의 생일", "🔐 관리자 모드"
    ])
    
    st.divider()
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# [메인 로직]
# ==========================================

# 1. 홈
if menu == "🏠 홈 대시보드":
    now = get_korea_time()
    weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    st.markdown(f"<div style='text-align: right; font-size: 1.5em; font-weight: bold; margin-bottom: 20px;'>📅 {now.strftime('%m월 %d일')} {weekdays[now.weekday()]}</div>", unsafe_allow_html=True)
    st.header("📢 오늘의 작전 브리핑")
    if not df_notice.empty:
        for i, row in df_notice.tail(10).iloc[::-1].iterrows():
            content = str(row.get('내용','')).strip()
            if not content: continue
            bg, border, icon = "#e8f5e9", "#4caf50", "✅"
            if "[상담]" in content: bg, border, icon = "#ffebee", "#ef5350", "📞"
            elif "[도복]" in content: bg, border, icon = "#e3f2fd", "#2196f3", "🥋"
            elif "심사" in content: bg, border, icon = "#fff9c4", "#fbc02d", "🏆"
            st.markdown(f"<div style='background:{bg}; border-left:5px solid {border}; padding:15px; margin-bottom:10px; border-radius:8px;'><b>{icon} 공지</b><br>{content}</div>", unsafe_allow_html=True)
    else: st.info("공지 없음")
    if not df_schedule.empty:
        today_test = df_schedule[pd.to_datetime(df_schedule.iloc[:,0].astype(str).str.replace('.','-'), errors='coerce').dt.date == now.date()]
        if not today_test.empty:
            st.error(f"🔥 오늘 승급심사: {len(today_test)}명")
            for _, r in today_test.iterrows(): st.write(f"- {r.iloc[1]}")

# 2. 차량
elif menu == "🚍 차량 운행표":
    st.header("🚍 통합 차량 운행표")
    now = get_korea_time()
    today_char = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    if not df_students.empty:
        w_df = df_students.copy()
        if '등원요일' in w_df.columns:
            w_df = w_df[w_df['등원요일'].astype(str).str.strip().eq('') | w_df['등원요일'].astype(str).str.contains(today_char)]
        for col in ['등원차량', '등원시간', '등원장소', '하원차량', '하원시간', '하원장소']:
            if col in w_df.columns: w_df[col] = w_df[col].apply(lambda x: parse_schedule_for_today(x, today_char))
        all_cars = sorted(list(set([x for x in w_df['등원차량'].unique().tolist() + w_df['하원차량'].unique().tolist() if x and str(x).strip()])))
        if all_cars:
            sel_car = st.selectbox("차량 선택", all_cars)
            sch_list = []
            for mode, v, t, l, c in [('등원','등원차량','등원시간','등원장소','등원확인'), ('하원','하원차량','하원시간','하원장소','하원확인')]:
                for _, r in w_df[w_df[v] == sel_car].iterrows():
                    sch_list.append({'name':r['이름'], 'type':mode, 'time':r.get(t,''), 'loc':r.get(l,''), 'status':r.get(c,''), 'col':c})
            sch_list.sort(key=lambda x: x['time'] if x['time'] else "99:99")
            for idx, item in enumerate(sch_list):
                bg = "#e3f2fd" if item['type']=='등원' else "#fff9c4"
                if item['status']=='결석': bg = "#ffebee"
                stat_mk = "✅" if item['status']=='탑승' else ("❌" if item['status']=='결석' else "")
                st.markdown(f"<div style='background:{bg}; padding:10px; margin-bottom:5px; border-radius:5px;'><b>{item['time']} {item['name']} ({item['type']})</b> {stat_mk}<br>{item['loc']}</div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                k = f"{idx}_{item['name']}_{item['type']}"
                if c1.button("탑승/취소", key=f"btn1_{k}"): 
                    update_check_status(item['name'], item['col'], "" if item['status']=="탑승" else "탑승")
                    st.rerun()
                if c2.button("결석/복구", key=f"btn2_{k}"):
                    update_check_status(item['name'], item['col'], "" if item['status']=="결석" else "결석")
                    st.rerun()
        else: st.info("배차 정보 없음")

# 3. 출석부
elif menu == "📝 수련부 출석":
    st.header("📝 수련부 출석부")
    now = get_korea_time()
    today_char = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    if not df_students.empty and '수련부' in df_students.columns:
        c1, c2 = st.columns([2, 1])
        query = c1.text_input("이름 검색")
        cls_list = sorted([str(x) for x in df_students['수련부'].unique() if str(x).strip()])
        sel_cls = c2.selectbox("수련부 선택", cls_list) if not query else None
        target = df_students
        if query: target = target[target['이름'].str.contains(query)]
        elif sel_cls: target = target[target['수련부'].astype(str) == sel_cls]
        if not target.empty:
            for i, row in target.sort_values('이름').iterrows():
                stat = row.get('출석확인', '')
                note = row.get('비고', '')
                bg = "#e8f5e9" if stat=='출석' else ("#ffebee" if stat=='결석' else "#ffffff")
                st.markdown(f"<div style='background:{bg}; padding:10px; border:1px solid #ddd; border-radius:5px; margin-top:5px;'><b>{row['이름']}</b> ({stat})<br><small>{note}</small></div>", unsafe_allow_html=True)
                b1, b2, b3 = st.columns([1,1,2])
                k = f"att_{i}_{row['이름']}"
                if b1.button("출석", key=f"ok_{k}"): 
                    update_check_status(row['이름'], "출석확인", "출석" if stat!="출석" else "")
                    st.rerun()
                if b2.button("결석", key=f"no_{k}"):
                    update_check_status(row['이름'], "출석확인", "결석" if stat!="결석" else "")
                    st.rerun()
                with st.expander("특이사항"):
                    new_note = st.text_input("사유", value=note, key=f"note_{k}")
                    if st.button("저장", key=f"s_{k}"):
                        update_check_status(row['이름'], "비고", new_note)
                        st.rerun()
        else: st.info("명단 없음")

# =========================================================
# [4. 정권연합 선수반]
# =========================================================
elif menu == "🏆 정권연합선수반":
    st.header("🏆 정권연합 2026 시즌 선수단 관제")
    sub_menu = st.radio("", ["👥 선수 등록/관리", "🏋️ 훈련/AI 분석"], horizontal=True)
    st.divider()

    if sub_menu == "👥 선수 등록/관리":
        st.subheader("👥 정권연합 선수 등록")
        with st.form("add_player_form"):
            new_name = st.text_input("선수 이름")
            new_team = st.text_input("소속", value="정권연합")
            new_note = st.text_input("비고")
            if st.form_submit_button("➕ 선수 명단에 추가"):
                if new_name:
                    if register_new_alliance_player(new_name, new_team, new_note):
                        st.success(f"{new_name} 등록 완료")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else: st.error("등록 실패")
                else: st.warning("이름을 입력하세요.")
        st.markdown("---")
        st.write("📋 **등록된 선수 목록**")
        athlete_list = get_alliance_athletes()
        if athlete_list: st.write(", ".join(athlete_list))
        else: st.warning("등록된 선수가 없습니다.")

    elif sub_menu == "🏋️ 훈련/AI 분석":
        athlete_list = get_alliance_athletes()
        if not athlete_list:
            st.error("⚠️ 등록된 선수가 없습니다. 먼저 등록해주세요.")
        else:
            t_name = st.selectbox("선수 선택", athlete_list)
            tab1, tab2, tab3 = st.tabs(["📝 채점/기록", "📹 AI 영상분석", "📊 기록 조회"])

            with tab1:
                st.subheader(f"📝 {t_name} 훈련 기록")
                with st.form("log"):
                    item = st.selectbox("종목", ["고려", "금강", "태백", "평원", "기초체력", "인터벌"])
                    phase = st.selectbox("주기", ["준비기", "특수준비기", "경기기", "회복기"])
                    st.write("---")
                    c_a, c_b = st.columns(2)
                    d01 = c_a.number_input("📉 0.1 감점", 0, 50, 0)
                    d03 = c_b.number_input("📉 0.3 감점", 0, 20, 0)
                    acc = max(0.0, 4.0 - d01*0.1 - d03*0.3)
                    st.metric("정확도 점수", f"{acc:.1f}")
                    st.markdown("---")
                    st.markdown("##### 표현력 (6.0)")
                    c_p1, c_p2, c_p3 = st.columns(3)
                    with c_p1: pres1 = st.slider("① 속도/힘", 0.0, 2.0, 1.0, 0.1)
                    with c_p2: pres2 = st.slider("② 리듬/강유", 0.0, 2.0, 1.0, 0.1)
                    with c_p3: pres3 = st.slider("③ 기의 표현", 0.0, 2.0, 1.0, 0.1)
                    pres_total = pres1 + pres2 + pres3
                    st.metric("표현력 총점", f"{pres_total:.1f}")
                    st.markdown(f"#### 🏁 총점: **{(acc + pres_total):.2f}**")
                    cmt = st.text_area("피드백")
                    if st.form_submit_button("저장"):
                        try:
                            client = get_gspread_client()
                            ws = client.open_by_key(SHEET_ID).worksheet("선수단기록")
                            ws.append_row([datetime.now().strftime("%Y-%m-%d"), t_name, "정권연합", item, acc, pres_total, d01, d03, acc+pres_total, phase, 5, cmt, ""])
                            st.success("저장 완료")
                        except: st.error("저장 실패")
            
            with tab2:
                st.subheader("📹 AI 분석")
                
                with st.expander("📂 링크 저장"):
                    lnk = st.text_input("유튜브 URL")
                    note = st.text_input("메모")
                    if lnk: st.video(lnk)
                    if st.button("링크 저장"):
                        try:
                            client = get_gspread_client()
                            ws = client.open_by_key(SHEET_ID).worksheet("선수단기록")
                            ws.append_row([datetime.now().strftime("%Y-%m-%d"), t_name, "정권연합", "링크", 0,0,0,0,0, "아카이브", 0, note, lnk])
                            st.success("저장됨")
                        except: st.error("오류")
                
                st.write("---")
                uf = st.file_uploader("영상 업로드", type=["mp4", "mov"])
                if uf:
                    st.video(uf)
                    if st.button("🚀 AI 분석 시작"):
                        with st.spinner("AI 분석 중..."):
                            try:
                                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                tfile.write(uf.read())
                                vf = genai.upload_file(tfile.name)
                                while vf.state.name == "PROCESSING": time.sleep(2); vf = genai.get_file(vf.name)
                                
                                # [최신 모델 우선 시도]
                                response = None
                                error_log = ""
                                model_list = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
                                
                                for m in model_list:
                                    try:
                                        model = genai.GenerativeModel(m)
                                        response = model.generate_content([vf, "태권도 품새 영상을 2025 KTA 규정으로 분석해줘."])
                                        if response:
                                            st.success(f"분석 완료 ({m})")
                                            break
                                    except Exception as e:
                                        error_log += f"[{m} 실패: {str(e)}] "
                                        continue
                                
                                if response:
                                    st.write(response.text)
                                else:
                                    st.error(f"분석 실패. 상세 원인: {error_log}")
                                
                                tfile.close(); os.unlink(tfile.name)
                            except Exception as e: st.error(f"업로드 오류: {e}")

            with tab3:
                if st.button("기록 불러오기"):
                    c = get_gspread_client()
                    try:
                        ws = c.open_by_key(SHEET_ID).worksheet("선수단기록")
                        d = ws.get_all_values()
                        df = pd.DataFrame(d[1:], columns=d[0])
                        st.dataframe(df[df['이름']==t_name])
                    except: st.warning("데이터 없음")

# 5. 상담
elif menu == "📞 학부모 상담":
    st.header("📞 상담 일지")
    q = st.text_input("원생 이름 입력")
    if q:
        with st.form("c_form"):
            ct = st.text_area("상담 내용")
            if st.form_submit_button("저장"):
                if add_consultation_log(q, ct): st.success("저장됨")
        st.write("---")
        logs = load_consultation_logs(q)
        if not logs.empty:
            for _, r in logs.iterrows(): st.info(f"**{r['날짜']}**: {r['내용']}")
    else: st.info("이름을 입력하세요")

# 6. 결석자
elif menu == "📉 오늘의 결석자":
    st.header("📉 결석자 현황")
    if not df_students.empty:
        absent = df_students[df_students['출석확인']=='결석']
        st.metric("오늘 결석", f"{len(absent)}명")
        if not absent.empty: st.dataframe(absent[['이름','수련부','비고']], hide_index=True)

# 7. 기질/훈육
elif menu == "🧠 기질/훈육 통합":
    st.header("🧠 기질/훈육 가이드")
    q = st.text_input("이름 검색")
    if q and not df_students.empty:
        r = df_students[df_students['이름']==q]
        if not r.empty:
            gt = r.iloc[0].get('기질유형', '미검사')
            st.subheader(f"{q} ({gt})")
            if gt!='미검사' and not df_guide.empty:
                g = df_guide[df_guide['기질유형']==gt]
                if not g.empty:
                    st.success(f"DO: {g.iloc[0].get('지도_DO(해라)')}")
                    st.warning(f"DON'T: {g.iloc[0].get('지도_DONT(하지마라)')}")
        else: st.error("원생 없음")

# 8. 승급심사
elif menu == "📈 승급심사 관리":
    st.header("📈 심사 일정")
    if not df_schedule.empty: st.dataframe(df_schedule, hide_index=True)

# 9. 생일
elif menu == "🎂 이달의 생일":
    st.header("🎂 이달의 생일자")
    st.info("기능 준비 중")

# 10. 관리자
elif menu == "🔐 관리자 모드":
    st.header("🔐 관리자")
    if st.text_input("비밀번호", type="password") == "0577":
        st.success("접속됨")
        if st.button("일일 마감 (출석부 저장 및 초기화)"):
            ok, msg = archive_daily_attendance()
            if ok:
                st.success(msg)
                try:
                    c = get_gspread_client()
                    ws = c.open_by_key(SHEET_ID).worksheet("원생명단")
                    h = ws.row_values(1)
                    ranges = []
                    for col in ["출석확인","등원확인","하원확인","비고"]:
                        if col in h:
                            idx = h.index(col)+1
                            let = gspread.utils.rowcol_to_a1(1, idx).replace('1','')
                            ranges.append(f"{let}2:{let}1000")
                    if ranges: ws.batch_clear(ranges)
                    st.success("초기화 완료")
                    time.sleep(1); st.rerun()
                except: st.error("초기화 실패")
            else: st.error(msg)
