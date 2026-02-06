import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import time
import google.generativeai as genai
import tempfile
import os

# ==========================================
# [설정] 로운태권도 구글 시트 ID
# ==========================================
SHEET_ID = "1fFNQQgYJfUzV-3qAdaFEeQt1OKBOJibASHQmeoW2nqo"

st.set_page_config(page_title="정권연합 통합 관제실", page_icon="🥋", layout="wide")

# [스타일 설정]
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

# [데이터 로드]
def load_data(sheet_name):
    client = get_gspread_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        if len(rows) < 2: return pd.DataFrame()
        return pd.DataFrame(rows[1:], columns=rows[0])
    except:
        return pd.DataFrame()

# 전역 데이터 로드
df_students = load_data("원생명단")
df_notice = load_data("공지사항")
df_schedule = load_data("심사일정")

# ==========================================
# UI 시작
# ==========================================
with st.sidebar:
    st.title("🥋 정권연합 총감독")
    st.markdown("**System Ver 5.0 (Alliance)**")
    st.write("---")
    
    # 메뉴 구성
    menu = st.radio("메뉴 선택", ["🏠 홈 대시보드", "🏆 정권연합 선수단", "🚍 차량/출석(원생용)", "🔐 관리자"])
    
    st.write("---")
    # AI 설정
    with st.expander("⚙️ AI 설정 (Gemini)"):
        api_key_input = st.text_input("API Key", type="password")
        if api_key_input:
            genai.configure(api_key=api_key_input)
            st.success("AI 가동 준비 완료")

# ==========================================
# 1. 홈 대시보드
# ==========================================
if menu == "🏠 홈 대시보드":
    now = get_korea_time()
    weekdays = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    st.markdown(f"<div style='text-align: right; font-size: 1.5em; font-weight: bold;'>📅 {now.strftime('%m월 %d일')} {weekdays[now.weekday()]}</div>", unsafe_allow_html=True)
    st.header("📢 연합 공지사항")
    if not df_notice.empty:
        for i, row in df_notice.tail(5).iloc[::-1].iterrows():
            st.info(f"📌 {row.get('내용', '-')}")
    else: st.write("등록된 공지가 없습니다.")

# ==========================================
# 2. 정권연합 선수단 (핵심 기능)
# ==========================================
elif menu == "🏆 정권연합 선수단":
    st.header("🏆 정권연합 선수단 통합 관리")
    
    # 훈련 프로그램 DB
    training_db = {
        "비시즌": ["🧘‍♂️ 회복/가동성", "- 폼롤러 및 스트레칭", "- 가벼운 러닝 20분"],
        "준비기": ["🏗️ 기초체력", "- 서킷 트레이닝", "- 기본동작 교정"],
        "경기기": ["🎯 실전대비", "- 모의 경기", "- 이미지 트레이닝"]
    }
    nlp_db = {
        "지면반력": "발바닥 전체로 지면을 강하게 밀어내십시오.",
        "허리쓰임": "골반의 회전력을 끝까지 전달하십시오.",
        "시선": "목표점을 끝까지 응시하십시오.",
        "호흡": "타격 순간 짧고 강하게 뱉으십시오."
    }

    # ------------------------------------
    # 선수 선택 (연합원 포함 로직)
    # ------------------------------------
    c1, c2 = st.columns([1, 1])
    with c1:
        # 원생명단에서 가져오기 + 직접 입력 옵션
        base_list = []
        if not df_students.empty and '이름' in df_students.columns:
            base_list = df_students[df_students['수련부'].astype(str).str.contains('선수|시범|입시', case=False, na=False)]['이름'].tolist()
        
        input_method = st.radio("선수 선택 방식", ["명단 선택", "직접 입력(타 소속/연합)"], horizontal=True)
        
        if input_method == "명단 선택":
            target_name = st.selectbox("이름 선택", base_list if base_list else ["데이터 없음"])
            target_team = "로운태권도" # 기본값
        else:
            target_name = st.text_input("이름 입력")
            target_team = st.text_input("소속 입력", value="정권연합")

    # ------------------------------------
    # 기능 탭
    # ------------------------------------
    tab1, tab2, tab3 = st.tabs(["📝 훈련 기록/채점", "📹 AI 영상 분석", "📊 데이터 조회"])

    # [Tab 1] 훈련 기록
    with tab1:
        st.subheader(f"📝 {target_name} ({target_team}) 훈련 기록")
        with st.form("training_log"):
            col_a, col_b = st.columns(2)
            poomsae = col_a.selectbox("훈련 종목", ["고려", "금강", "태백", "평원", "기초체력", "인터벌"])
            phase = col_b.selectbox("훈련 주기", ["준비기", "특수준비기", "경기기", "회복기"])
            
            st.markdown("---")
            c_score1, c_score2 = st.columns(2)
            d01 = c_score1.number_input("0.1 감점", 0, 50, 0)
            d03 = c_score1.number_input("0.3 감점", 0, 20, 0)
            acc = max(0, 4.0 - (d01 * 0.1) - (d03 * 0.3))
            c_score1.metric("정확도 (4.0)", f"{acc:.1f}")
            
            pres = c_score2.slider("표현력 (6.0)", 0.0, 6.0, 3.0, 0.1)
            c_score2.metric("표현력", f"{pres:.1f}")
            
            st.markdown("---")
            keyword = st.multiselect("코칭 키워드", list(nlp_db.keys()))
            auto_cmt = " ".join([nlp_db[k] for k in keyword])
            comment = st.text_area("피드백", value=auto_cmt)
            rpe = st.slider("운동 강도(RPE)", 1, 10, 5)
            
            if st.form_submit_button("기록 저장"):
                if target_name:
                    try:
                        client = get_gspread_client()
                        ws = client.open_by_key(SHEET_ID).worksheet("선수단기록")
                        today = datetime.now().strftime("%Y-%m-%d")
                        total = acc + pres
                        # [날짜, 이름, 소속, 종목, 정확도, 표현력, 감점0.1, 감점0.3, 총점, 주기, RPE, 코멘트, 링크]
                        ws.append_row([today, target_name, target_team, poomsae, acc, pres, d01, d03, total, phase, rpe, comment, ""])
                        st.success("저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
                else:
                    st.warning("이름을 입력해주세요.")

    # [Tab 2] AI 영상 분석
    with tab2:
        st.subheader("📹 AI 정밀 분석")
        
        # 링크 아카이빙
        with st.expander("📂 영상 링크 저장"):
            link_url = st.text_input("유튜브/드라이브 URL")
            link_note = st.text_input("영상 설명")
            if st.button("링크만 저장"):
                if target_name and link_url:
                    try:
                        client = get_gspread_client()
                        ws = client.open_by_key(SHEET_ID).worksheet("선수단기록")
                        today = datetime.now().strftime("%Y-%m-%d")
                        ws.append_row([today, target_name, target_team, "영상기록", 0,0,0,0,0, "아카이브", 0, link_note, link_url])
                        st.success("링크 저장 완료")
                    except: st.error("저장 오류")

        # 파일 업로드 분석
        st.markdown("---")
        uploaded_file = st.file_uploader("영상 파일 업로드 (MP4)", type=["mp4", "mov"])
        if uploaded_file and api_key_input:
            st.video(uploaded_file)
            if st.button("🚀 AI 분석 시작"):
                with st.spinner("분석 중..."):
                    try:
                        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                        tfile.write(uploaded_file.read())
                        vfile = genai.upload_file(tfile.name)
                        while vfile.state.name == "PROCESSING":
                            time.sleep(2)
                            vfile = genai.get_file(vfile.name)
                        
                        model = genai.GenerativeModel('gemini-1.5-pro-latest')
                        res = model.generate_content([vfile, "이 태권도 품새 영상을 2025 KTA 규정으로 분석해줘. 점수 예측과 감점 요인을 상세히 알려줘."])
                        st.markdown(res.text)
                        tfile.close(); os.unlink(tfile.name)
                    except: st.error("분석 오류")

    # [Tab 3] 데이터 조회
    with tab3:
        st.subheader("📊 기록 조회")
        if st.button("기록 불러오기"):
            df_log = load_data("선수단기록")
            if not df_log.empty:
                # 해당 선수 필터링
                my_log = df_log[df_log['이름'] == target_name]
                if not my_log.empty:
                    st.dataframe(my_log)
                else:
                    st.info(f"{target_name} 선수의 기록이 없습니다.")
            else:
                st.warning("저장된 데이터가 없습니다.")

# ==========================================
# 3. 차량/출석 (기존 원생용 기능)
# ==========================================
elif menu == "🚍 차량/출석(원생용)":
    st.header("🚍 원생 차량 및 출석 관리")
    
    tab_bus, tab_att = st.tabs(["차량 운행", "출석부"])
    
    with tab_bus:
        if not df_students.empty and '등원차량' in df_students.columns:
            st.dataframe(df_students[['이름', '등원차량', '하원차량']], hide_index=True)
    
    with tab_att:
        if not df_students.empty:
            st.dataframe(df_students[['이름', '수련부', '출석확인']], hide_index=True)

# ==========================================
# 4. 관리자
# ==========================================
elif menu == "🔐 관리자":
    st.header("🔐 관리자 모드")
    if st.text_input("비밀번호", type="password") == "0577":
        st.success("접속 허용")
        if st.button("일일 데이터 초기화"):
            # (초기화 로직 생략 - 필요 시 기존 코드 참조)
            st.info("초기화 기능은 안전을 위해 비활성화 상태입니다.")
