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

# --- 신청 완료 메시지 표시 로직 ---
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.session_state.submitted:
    st.success(f"🎉 신청이 정상적으로 완료되었습니다! [{st.session_state.last_class}]")
    st.balloons()
    st.session_state.submitted = False

# --- 구글 시트 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 핵심 수정 부분: ttl=0 을 추가하여 실시간으로 데이터를 가져옵니다.
def load_data():
    return conn.read(spreadsheet=SHEET_URL, usecols=[0,1,2,3,4], ttl=0)

# --- UI 구성 ---
st.title("⛪ 원데이클래스 선착순 신청")

try:
    df_current = load_data()
    # 데이터가 아예 없는 경우를 대비한 처리
    df_current = df_current.dropna(how="all")
    if '클래스' not in df_current.columns:
        df_current['클래스'] = ""
except:
    df_current = pd.DataFrame(columns=["신청시간", "이름", "셀이름", "연락처", "클래스"])

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

if not display_options:
    st.error("🚨 모든 클래스가 마감되었습니다.")
else:
    with st.form("registration_form", clear_on_submit=True):
        name = st.text_input("이름")
        cell_name = st.text_input("셀 이름")
        phone = st.text_input("연락처")
        class_choice = st.selectbox("원하시는 클래스를 선택하세요", display_options)
        submit_button = st.form_submit_button("신청하기")

        if submit_button:
            try:
                # 신청 시점에도 최신 데이터를 다시 불러와 정원 확인
                df_latest = load_data().dropna(how="all")
                latest_counts = df_latest['클래스'].value_counts().to_dict()
            except:
                latest_counts = {}
                
            current_latest = latest_counts.get(class_choice, 0)
            
            if not name or not cell_name or not phone:
                st.warning("모든 정보를 입력해주세요.")
            elif current_latest >= CLASS_CAPACITY[class_choice]:
                st.error(f"앗! 그새 '{class_choice}' 클래스가 마감되었습니다.")
            else:
                new_row = pd.DataFrame([{
                    "신청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "이름": name, "셀이름": cell_name, "연락처": phone, "클래스": class_choice
                }])
                updated_df = pd.concat([df_current, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                
                st.session_state.submitted = True
                st.session_state.last_class = class_choice
                st.rerun()

st.write("\n" * 5)
st.divider()

with st.expander("🛠️ 관리자 메뉴 (비밀번호 필요)"):
    input_pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if input_pw == ADMIN_PASSWORD:
        st.success("인증되었습니다.")
        st.subheader("📝 전체 신청 명단")
        # 관리자 메뉴에서도 최신 데이터를 즉시 불러옵니다.
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
