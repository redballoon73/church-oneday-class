import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Z253UxncrohN_NnL9xxjorkiKAlkH6gysjeyyT-ZihU/edit?pli=1&gid=0#gid=0"
ADMIN_PASSWORD = "church1234"

CLASS_CAPACITY = {
    "미니올림픽": 4,
    "무드등 만들기": 4,
    "꽃꽂이": 2,
    "토이 쿠키 만들기": 3,
    "키캡+볼펜 꾸미기": 3,
    "서지컬 팔찌 만들기": 3,
    "버터떡 만들기": 3
}
CLASS_LIST = list(CLASS_CAPACITY.keys())

st.set_page_config(page_title="교회 원데이클래스 신청", page_icon="⛪")

# --- 구글 시트 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# [최적화 1] 일반 조회용: 10초간 데이터를 캐싱하여 구글 API 부하를 줄임
def load_data_fast():
    return conn.read(spreadsheet=SHEET_URL, usecols=[0,1,2,3,4], ttl=10)

# [최적화 2] 신청/취소 로직용: 캐싱 없이 즉시 최신 데이터를 가져옴
def load_data_fresh():
    return conn.read(spreadsheet=SHEET_URL, usecols=[0,1,2,3,4], ttl=0)

# --- UI 구성 ---
st.title("⛪ 원데이클래스 선착순 신청")

# 초기 화면용 데이터 (캐싱 적용)
try:
    df_current = load_data_fast().dropna(how="all")
except:
    df_current = pd.DataFrame(columns=["신청시간", "이름", "셀이름", "연락처", "클래스"])

# 클래스별 잔여 현황 계산
class_counts = df_current['클래스'].value_counts().to_dict()

st.subheader("📊 클래스별 잔여 현황")
cols = st.columns(2)
display_options = []

for i, class_name in enumerate(CLASS_LIST):
    max_cap = CLASS_CAPACITY[class_name]
    current = class_counts.get(class_name, 0)
    remain = max_cap - current
    
    with cols[i % 2]:
        if remain > 0:
            st.write(f"✅ **{class_name}**: {current}/{max_cap}명 (잔여 {remain}자리)")
            display_options.append(class_name)
        else:
            st.write(f"❌ **{class_name}**: {max_cap}/{max_cap}명 **[마감]**")

st.divider()

# --- 신청 및 확인 로직 ---
st.subheader("📝 신청하기 및 내역 확인")
c1, c2 = st.columns(2)
with c1:
    user_name = st.text_input("이름을 입력하세요", placeholder="홍길동")
with c2:
    user_cell = st.text_input("셀 이름을 입력하세요", placeholder="사랑셀")

if user_name and user_cell:
    # 1단계: 캐시된 데이터로 중복 여부 1차 확인
    existing_user = df_current[(df_current['이름'] == user_name) & (df_current['셀이름'] == user_cell)]
    
    if not existing_user.empty:
        registered_class = existing_user.iloc[0]['클래스']
        st.info(f"📍 **{user_name}** 님( **{user_cell}** )은 이미 [**{registered_class}**] 에 신청되어 있습니다.")
        
        if st.button(f"🗑️ '{registered_class}' 신청 취소하기"):
            # 취소 시점에 최신 데이터 재로드 (다른 사람 기록 삭제 방지)
            df_latest = load_data_fresh().dropna(how="all")
            updated_df = df_latest[~((df_latest['이름'] == user_name) & (df_latest['셀이름'] == user_cell))]
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            st.success("신청이 취소되었습니다.")
            st.rerun()
            
    else:
        if not display_options:
            st.error("🚨 모든 클래스가 마감되었습니다.")
        else:
            with st.form("registration_form", clear_on_submit=True):
                user_phone = st.text_input("연락처를 입력하세요", placeholder="010-1234-5678")
                class_choice = st.selectbox("원하시는 클래스를 선택하세요", display_options)
                submit_button = st.form_submit_button("신청 완료")

                if submit_button:
                    # [최적화 3] 버튼 클릭 순간 '실시간' 데이터 로드
                    df_realtime = load_data_fresh().dropna(how="all")
                    
                    # 실시간 중복 체크 및 정원 체크
                    is_duplicate = not df_realtime[(df_realtime['이름'] == user_name) & (df_realtime['셀이름'] == user_cell)].empty
                    current_count = df_realtime[df_realtime['클래스'] == class_choice].shape[0]

                    if not user_phone:
                        st.warning("연락처를 입력해주세요.")
                    elif is_duplicate:
                        st.error("이미 신청 내역이 존재합니다.")
                    elif current_count >= CLASS_CAPACITY[class_choice]:
                        st.error(f"앗! 그새 '{class_choice}' 클래스가 마감되었습니다.")
                    else:
                        new_row = pd.DataFrame([{
                            "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "이름": user_name, 
                            "셀이름": user_cell, 
                            "연락처": user_phone, 
                            "클래스": class_choice
                        }])
                        # [최적화 4] 방금 읽은 실시간 데이터에 합쳐서 업데이트 (데이터 유실 방지)
                        updated_df = pd.concat([df_realtime, new_row], ignore_index=True)
                        conn.update(spreadsheet=SHEET_URL, data=updated_df)
                        
                        st.success(f"🎉 신청이 완료되었습니다!")
                        st.balloons()
                        st.rerun()
else:
    st.write("위의 정보를 입력하면 신청 확인 및 신규 신청이 가능합니다.")

# --- 관리자 메뉴 ---
st.divider()
with st.expander("🛠️ 관리자 메뉴"):
    input_pw = st.text_input("비밀번호", type="password")
    if input_pw == ADMIN_PASSWORD:
        admin_df = load_data_fresh().dropna(how="all")
        st.dataframe(admin_df, use_container_width=True)
