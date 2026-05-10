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
    "꽃꽂이": 3,
    "토이 쿠키 만들기": 3,
    "키캡+볼펜 꾸미기": 3,
    "서지컬 팔찌 만들기": 3,
    "버터떡 만들기": 3
}
CLASS_LIST = list(CLASS_CAPACITY.keys())

st.set_page_config(page_title="교회 원데이클래스 신청", page_icon="⛪")

# --- 구글 시트 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=SHEET_URL, usecols=[0,1,2,3,4], ttl=0)

# --- UI 구성 ---
st.title("⛪ 원데이클래스 선착순 신청")

# 데이터 로드
try:
    df_current = load_data().dropna(how="all")
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
    # 1. 중복 신청 여부 확인 (이름과 셀 이름 모두 일치해야 함)
    existing_user = df_current[(df_current['이름'] == user_name) & (df_current['셀이름'] == user_cell)]
    
    if not existing_user.empty:
        # 이미 신청한 경우
        registered_class = existing_user.iloc[0]['클래스']
        st.info(f"📍 **{user_name}** 님( **{user_cell}** )은 이미 [**{registered_class}**] 클래스에 신청하셨습니다.")
        
        st.warning("신청 내역을 변경하시려면 먼저 취소 버튼을 눌러주세요.")
        if st.button(f"🗑️ '{registered_class}' 신청 취소하기"):
            # 이름과 셀 이름이 모두 일치하는 행만 삭제
            updated_df = df_current[~((df_current['이름'] == user_name) & (df_current['셀이름'] == user_cell))]
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            st.success("신청이 정상적으로 취소되었습니다. 다시 신청해 주세요!")
            st.rerun()
            
    else:
        # 신청하지 않은 경우: 신청 폼 표시
        if not display_options:
            st.error("🚨 모든 클래스가 마감되었습니다.")
        else:
            with st.form("registration_form", clear_on_submit=True):
                st.write(f"👉 **{user_name}** 님( **{user_cell}** ), 나머지 정보를 입력해 주세요.")
                user_phone = st.text_input("연락처를 입력하세요", placeholder="010-1234-5678")
                class_choice = st.selectbox("원하시는 클래스를 선택하세요", display_options)
                submit_button = st.form_submit_button("신청 완료")

                if submit_button:
                    # 실시간 잔여석 재확인
                    try:
                        df_latest = load_data().dropna(how="all")
                        latest_counts = df_latest['클래스'].value_counts().to_dict()
                    except:
                        latest_counts = {}
                    
                    if not user_phone:
                        st.warning("연락처를 입력해주세요.")
                    elif latest_counts.get(class_choice, 0) >= CLASS_CAPACITY[class_choice]:
                        st.error(f"앗! 그새 '{class_choice}' 클래스가 마감되었습니다.")
                    else:
                        new_row = pd.DataFrame([{
                            "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "이름": user_name, 
                            "셀이름": user_cell, 
                            "연락처": user_phone, 
                            "클래스": class_choice
                        }])
                        updated_df = pd.concat([df_current, new_row], ignore_index=True)
                        conn.update(spreadsheet=SHEET_URL, data=updated_df)
                        
                        st.success(f"🎉 신청이 완료되었습니다!")
                        st.balloons()
                        st.rerun()
else:
    st.write("위의 **이름 ** 과 **셀 이름 ** 을 모두 입력하면 신청 확인 및 신규 신청이 가능합니다.")

# --- 관리자 메뉴 ---
st.write("\n" * 5)
st.divider()

with st.expander("🛠️ 관리자 메뉴 (비밀번호 필요)"):
    input_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if input_pw == ADMIN_PASSWORD:
        st.success("인증되었습니다.")
        st.subheader("📝 전체 신청 명단")
        admin_df = load_data().dropna(how="all")
        st.dataframe(admin_df, use_container_width=True)
        
        csv = admin_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="엑셀(CSV) 파일로 다운로드",
            data=csv,
            file_name=f"신청현황_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv",
        )
    elif input_pw != "":
        st.error("비밀번호가 틀렸습니다.")
