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

# 화이트 테마 강제 고정 (글씨 검정)
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF; }
        [data-testid="stSidebar"] { background-color: #F0F2F6; }
        h1, h2, h3, h4, h5, h6, p, span, div { color: #31333F; }
        .stTextInput input { color: #31333F; }
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

# [핵심] 데이터 쓰기 함수
def update_check_status(student_name, col_name, status_value):
    client = get_gspread_client()
    if not client: return

    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("원생명단")
        
        try:
            cell = worksheet.find(student_name)
            row_num = cell.row
            
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

# 요일별 스케줄 파싱
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
            if today_char in days:
                return val
    return ""

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
    st.markdown("**System Ver 46.0 (Color Cards)**")
    
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

# [2] 차량 운행표 (디자인 개선: 이름 크게, 시간 구분)
elif menu == "🚍 차량 운행표":
    st.header("🚍 실시간 통합 운행표")
    
    now = get_korea_time()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    today_char = weekdays_kr[now.weekday()]
    
    st.caption(f"📅 **오늘({today_char}요일)** 시간순 전체 리스트 (🟦등원 / 🟨하원)")

    if not df_students.empty:
        working_df = df_students.copy()
        
        # 스마트 파싱
        for col in ['등원차량', '등원시간', '등원장소', '하원차량', '하원시간', '하원장소']:
            if col in working_df.columns:
                working_df[col] = working_df[col].apply(lambda x: parse_schedule_for_today(x, today_char))
        
        if '차량이용여부' in working_df.columns:
            working_df = working_df[working_df['차량이용여부'].fillna('O').astype(str).str.contains('O|이용|사용|오|ㅇ', case=False)]

        # 차량 선택
        cars_in = working_df['등원차량'].unique().tolist()
        cars_out = working_df['하원차량'].unique().tolist()
        all_cars = sorted(list(set([x for x in cars_in + cars_out if x and str(x).strip() != ''])))
        
        if all_cars:
            selected_car = st.selectbox("배차 선택", all_cars)
            
            schedule_list = []
            
            # 등원 수집
            in_df = working_df[working_df['등원차량'] == selected_car]
            for _, row in in_df.iterrows():
                schedule_list.append({
                    'name': row['이름'],
                    'type': '등원',
                    'time': row.get('등원시간', ''),
                    'loc': row.get('등원장소', ''),
                    'status': row.get('등원확인', ''),
                    'check_col': '등원확인'
                })
                
            # 하원 수집
            out_df = working_df[working_df['하원차량'] == selected_car]
            for _, row in out_df.iterrows():
                schedule_list.append({
                    'name': row['이름'],
                    'type': '하원',
                    'time': row.get('하원시간', ''),
                    'loc': row.get('하원장소', ''),
                    'status': row.get('하원확인', ''),
                    'check_col': '하원확인'
                })
            
            # 시간순 정렬
            def time_sort_key(val):
                t = str(val['time']).strip()
                if not t: return "99:99" 
                return t.zfill(5) 
            
            schedule_list.sort(key=time_sort_key)
            
            # 진행률
            total_cnt = len(schedule_list)
            done_cnt = len([x for x in schedule_list if x['status'] in ['탑승', '결석']])
            st.progress(done_cnt / total_cnt if total_cnt > 0 else 0)
            
            current_time_group = None
            
            for idx, item in enumerate(schedule_list):
                time_display = item['time'] if item['time'] else "시간 미정"
                
                # [디자인] 시간 구분선 (시간이 바뀔 때마다 표시)
                if time_display != current_time_group:
                    st.markdown("---")
                    st.subheader(f"⏰ {time_display}")
                    current_time_group = time_display
                
                # [디자인] 박스 색상 (등원=info/파랑, 하원=warning/노랑)
                if item['type'] == '등원':
                    box_func = st.info
                    label = "🟦 등원"
                else:
                    box_func = st.warning
                    label = "🟨 하원"
                
                is_done = (item['status'] == '탑승')
                is_absent = (item['status'] == '결석')
                
                # 카드 출력
                with box_func(f"{label}"): # 헤더는 간단하게
                    c1, c2, c3 = st.columns([3, 1, 1])
                    
                    with c1:
                        # [핵심] 이름을 여기서 크게 출력!
                        st.markdown(f"#### 🥋 {item['name']}")
                        st.write(f"📍 {item['loc']}")
                        if is_done: st.caption("✅ 탑승 완료")
                        if is_absent: st.caption("❌ 결석")
                        
                    with c2:
                        if is_done:
                            if st.button("취소", key=f"undo_{idx}_{item['name']}_{item['type']}"):
                                update_check_status(item['name'], item['check_col'], '')
                                st.rerun()
                        else:
                            # 탑승 버튼
                            if st.button("탑승", key=f"ride_{idx}_{item['name']}_{item['type']}"):
                                update_check_status(item['name'], item['check_col'], '탑승')
                                st.rerun()
                                
                    with c3:
                        if is_absent:
                            if st.button("복구", key=f"unabs_{idx}_{item['name']}_{item['type']}"):
                                update_check_status(item['name'], item['check_col'], '')
                                st.rerun()
                        else:
                            # 결석 버튼
                            if st.button("결석", key=f"abs_{idx}_{item['name']}_{item['type']}"):
                                update_check_status(item['name'], item['check_col'], '결석')
                                st.rerun()

        else:
            st.info("오늘 운행하는 차량이 없습니다.")
    else:
        st.error("데이터 로드 실패")

# [3] 수련부 출석
elif menu == "📝 수련부 출석":
    st.header("📝 수련부별 출석 체크")
    if '수련부' in df_students.columns:
        raw_classes = df_students['수련부'].dropna().unique()
        class_list = sorted([str(x) for x in raw_classes if str(x).strip() != ''])
        
        if class_list:
            now = get_korea_time()
            weekdays = ["월", "화", "수", "목", "금", "토", "일"]
            today_char = weekdays[now.weekday()]
            
            c_filter, c_select = st.columns([1, 2])
            with c_filter:
                show_today_only = st.toggle(f"📅 오늘({today_char})만 보기", value=True)
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
            st.caption("※ '결석' 버튼을 누르면 차량 스케줄도 '결석' 처리됩니다.")
            
            check_col = "출석확인"
            note_col = "비고"
            
            for i, row in class_students.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    current_val = row.get(check_col, '')
                    current_note = row.get(note_col, '')
                    is_checked = (current_val == '출석')
                    
                    with c1:
                        st.subheader(f"{row['이름']}")
                        if current_val == '출석':
                            st.markdown(":green[✅ 출석 완료]")
                        elif current_val == '결석':
                            st.markdown(":red[❌ 결석]")
                        if current_note and str(current_note) != 'nan':
                            st.caption(f"📌 {current_note}")

                    with c2:
                        new_check = st.checkbox("출석", value=is_checked, key=f"att_{i}_{row['이름']}")
                        if new_check != is_checked:
                            new_status = '출석' if new_check else ''
                            update_check_status(row['이름'], check_col, new_status)
                            st.rerun()

                    with c3:
                        if current_val == '결석':
                             if st.button("취소", key=f"cncl_{i}_{row['이름']}"):
                                update_check_status(row['이름'], check_col, '')
                                st.rerun()
                        else:
                            if st.button("결석", key=f"abs_{i}_{row['이름']}"):
                                update_check_status(row['이름'], check_col, '결석')
                                st.rerun()

                    with st.expander("🔽 특이사항 / 빠른 입력"):
                        t1, t2, t3, t4 = st.columns(4)
                        with t1:
                            if st.button("🤒병결", key=f"sick_{i}"):
                                update_check_status(row['이름'], note_col, "병결")
                                st.rerun()
                        with t2:
                            if st.button("✈여행", key=f"trip_{i}"):
                                update_check_status(row['이름'], note_col, "여행")
                                st.rerun()
                        with t3:
                            if st.button("🤕부상", key=f"hurt_{i}"):
                                update_check_status(row['이름'], note_col, "부상")
                                st.rerun()
                        with t4:
                            if st.button("🗑지움", key=f"del_{i}"):
                                update_check_status(row['이름'], note_col, "")
                                st.rerun()
                        
                        safe_note = current_note if str(current_note) != 'nan' else ""
                        new_note = st.text_input("직접 입력", value=safe_note, key=f"note_in_{i}")
                        if new_note != safe_note:
                            update_check_status(row['이름'], note_col, new_note)
                            st.rerun()
        else:
            st.info("수련부 데이터가 없습니다.")
    else:
        st.error("엑셀에 '수련부' 컬럼이 없습니다.")

# [4] 오늘의 결석자
elif menu == "📉 오늘의 결석자":
    st.header("📉 오늘의 결석 현황")
    
    if '출석확인' in df_students.columns:
        absent_list = df_students[df_students['출석확인'] == '결석']
        if '수련부' in absent_list.columns:
            absent_list = absent_list.sort_values(by='수련부')
        
        count = len(absent_list)
        st.metric("오늘 총 결석", f"{count}명")
        
        st.markdown("---")
        
        if count > 0:
            cols_to_show = ['이름', '수련부', '비고']
            if '비고' not in absent_list.columns:
                cols_to_show = ['이름', '수련부']
            st.dataframe(absent_list[cols_to_show], use_container_width=True, hide_index=True)
        else:
            st.balloons()
            st.success("🎉 와우! 현재까지 결석자가 한 명도 없습니다. (전원 출석)")
    else:
        st.error("엑셀에 '출석확인' 데이터가 없습니다.")

# [5] 기질/훈육 통합
elif menu == "🧠 기질/훈육 통합":
    st.header("🧠 원생 맞춤형 훈육 가이드")
    st.info("💡 아이 이름을 검색하면 기질 정보와 훈육법을 한 번에 보여줍니다.")
    col1, col2 = st.columns([1, 2])
    with col1:
        search_name = st.text_input("원생 이름 검색", placeholder="예: 김지안")
    if search_name:
        student = df_students[df_students['이름'] == search_name]
        if not student.empty:
            s_data = student.iloc[0]
            g_type = s_data.get('기질유형', '미검사')
            st.divider()
            st.subheader(f"🥋 {s_data['이름']}")
            i1, i2, i3 = st.columns(3)
            i1.metric("수련부", s_data.get('수련부', '-'))
            i2.metric("현재급", s_data.get('단', s_data.get('현재급', '-')))
            i3.metric("기질유형", g_type)
            if g_type != '미검사' and not df_guide.empty:
                guide_match = df_guide[df_guide['기질유형'] == g_type]
                if not guide_match.empty:
                    g_row = guide_match.iloc[0]
                    st.success(f"✨ **{g_type}** 아이를 위한 지도 전략")
                    with st.container(border=True):
                        st.markdown(f"**🎯 핵심 특징:**")
                        st.write(g_row.get('핵심특징', '-'))
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info("**🙆‍♂️ 이렇게 해주세요 (DO)**")
                        st.write(g_row.get('지도_DO(해라)', '-'))
                    with c2:
                        st.error("**🙅‍♂️ 이건 피해주세요 (DON'T)**")
                        st.write(g_row.get('지도_DONT(하지마라)', '-'))
                    with st.expander("💬 상황별 훈육 스크립트 (말하기 예시)"):
                        st.code(g_row.get('훈육_스크립트', '데이터 없음'), language='text')
                else:
                    st.warning("가이드 데이터에서 해당 기질을 찾을 수 없습니다.")
            else:
                st.warning("기질 검사가 진행되지 않았거나, 데이터가 없습니다.")
        else:
            st.error("검색된 원생이 없습니다.")

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
                    if '등원요일' in s_data:
                         st.write(f"**등원요일:** {s_data['등원요일']}")
                else:
                    st.error("검색된 원생이 없습니다.")
        with tab2:
            st.subheader("데이터 초기화")
            st.warning("⚠️ 하루 일과가 끝나면 눌러주세요. (등원/하원/출석/비고 기록을 모두 지웁니다)")
            if st.button("🔥 하루 마감 (전체 삭제)"):
                with st.spinner("구글 시트 청소 중..."):
                    try:
                        client = get_gspread_client()
                        sh = client.open_by_key(SHEET_ID)
                        ws = sh.worksheet("원생명단")
                        cols_to_clear = ["등원확인", "하원확인", "출석확인", "비고"]
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
