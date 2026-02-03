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

# ==========================================
# 🚑 [긴급 진단] 연결 테스트 섹션
# ==========================================
st.error("🚑 [시스템 진단 모드] 실행 중... (문제가 해결되면 코드를 다시 요청하세요)")

try:
    # 1. 키 확인
    if "gcp_service_account" not in st.secrets:
        st.error("❌ Secrets에 'gcp_service_account'가 없습니다. 설정 단계를 확인하세요.")
        st.stop()
    
    # 2. 구글 접속 시도
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(credentials)
    st.write("✅ 구글 클라우드 접속 성공!")
    
    # 3. 엑셀 파일 열기 시도
    sh = client.open_by_key(SHEET_ID)
    st.write(f"✅ 엑셀 파일('{sh.title}') 찾음!")
    
    # 4. 탭 이름 확인
    worksheet_list = [ws.title for ws in sh.worksheets()]
    st.info(f"📋 현재 엑셀에 있는 탭 목록: {worksheet_list}")
    
    if "원생명단" not in worksheet_list:
        st.error("🚨 중요: 엑셀에 '원생명단'이라는 탭이 없습니다! (띄어쓰기 확인해보세요)")
    else:
        st.success("✅ '원생명단' 탭 확인됨. 연결 상태 정상!")

except Exception as e:
    st.error(f"❌ 연결 실패! 아래 에러 메시지를 관장님께 보여주세요:\n\n{e}")
    st.stop() # 에러 나면 여기서 멈춤

# ==========================================
# (아래는 정상 작동 시 실행되는 기존 코드)
# ==========================================

def get_korea_time():
    return datetime.utcnow() + timedelta(hours=9)

@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(credentials)
    return client

@st.cache_data(ttl=3)
def load_data_from_sheet(sheet_name):
    client = get_gspread_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df = df.astype(str) 
        return df
    except Exception as e:
        return pd.DataFrame()

def update_check_status(student_name, col_name, status_value):
    client = get_gspread_client()
    sh = client.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("원생명단")
    
    try:
        cell = worksheet.find(student_name)
        row_num = cell.row
        header_cell = worksheet.find(col_name)
        col_num = header_cell.col
        worksheet.update_cell(row_num, col_num, status_value)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"저장 오류: {e}")

df_students = load_data_from_sheet("원생명단") 
df_notice = load_data_from_sheet("공지사항")
df_guide = load_data_from_sheet("기질가이드")
df_schedule = load_data_from_sheet("심사일정")

with st.sidebar:
    st.title("🥋 로운태권도")
    st.caption("진단 모드")
    
    menu = st.radio("메뉴 선택", [
        "🏠 홈 대시보드", 
        "🚍 차량 운행표", 
        "📝 수련부 출석", 
        "🔐 관리자 모드"
    ])
    
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

if menu == "🏠 홈 대시보드":
    st.header("대시보드 (진단중)")
    if not df_students.empty:
        st.success(f"데이터 로드 성공! 총 {len(df_students)}명")
        st.dataframe(df_students.head())
    else:
        st.error("데이터가 비어있습니다.")

elif menu == "🚍 차량 운행표":
    st.header("차량 운행표 (진단중)")
    mode = st.radio("운행 모드", ["등원", "하원"], horizontal=True)
    if mode == "등원":
        col_chk = "등원확인"
        col_car = "등원차량"
    else:
        col_chk = "하원확인"
        col_car = "하원차량"
        
    if not df_students.empty and col_car in df_students.columns:
        target = df_students[df_students[col_car].notna() & (df_students[col_car] != '')]
        car_list = sorted(target[col_car].unique().tolist())
        sel_car = st.selectbox("차량", car_list)
        final_df = target[target[col_car] == sel_car]
        
        for i, row in final_df.iterrows():
            c1, c2 = st.columns(2)
            c1.write(f"{row['이름']}")
            if st.button("탑승", key=f"btn_{i}"):
                update_check_status(row['이름'], col_chk, '탑승')
                st.rerun()

elif menu == "📝 수련부 출석":
    st.write("출석부 화면")

elif menu == "🔐 관리자 모드":
    st.write("관리자 화면")
