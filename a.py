import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 초기 설정 및 최적화 도구 (Config & Utils)
# ---------------------------------------------------------
st.set_page_config(page_title="Hanwoo Calf Manager Pro", layout="wide", page_icon="🐂")

# [최적화] 상태 초기화 (if문 최소화)
if 'calves_db' not in st.session_state:
    st.session_state.calves_db = [] 
if 'health_logs' not in st.session_state:
    st.session_state.health_logs = []

# [최적화] ID 생성 함수 (문자열 포맷팅 활용)
def generate_id(date_obj, mother, sex):
    return f"{date_obj.strftime('%y%m%d')}-{mother}-{sex}"

# [최적화] ADG 계산 함수
def get_adg(birth_weight, current_weight, birth_date):
    days = (datetime.now() - birth_date).days
    return (current_weight - birth_weight) / days if days > 0 else 0, days

# ---------------------------------------------------------
# 2. 사이드바: 개체 선택 (The Bridge)
# ---------------------------------------------------------
st.sidebar.title("🐂 개체 선택 시스템")

# DB에서 ID 리스트 추출 (List Comprehension)
calf_options = [c['id'] for c in st.session_state.calves_db]

# 선택된 개체 ID
selected_id = st.sidebar.selectbox(
    "관리할 송아지를 선택하세요", 
    options=calf_options if calf_options else ["등록된 개체 없음"]
)

# [최적화] 선택된 개체 데이터 가져오기 (for문+if문 대신 next() 사용)
current_calf = next((c for c in st.session_state.calves_db if c['id'] == selected_id), None)

# ---------------------------------------------------------
# 3. 메인 인터페이스 (Tabs)
# ---------------------------------------------------------
st.title("한우 송아지 정밀 통합 관리 시스템")
tab_register, tab_manage = st.tabs(["📸 신규 개체 등록", "📊 개체 정밀 관리"])

# =========================================================
# [Tab 1] 신규 등록 (Create)
# =========================================================
with tab_register:
    st.subheader("신규 송아지 출생 신고")
    
    with st.form("reg_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            in_date = st.date_input("출생일", datetime.now())
            in_mother = st.text_input("어미 번호 (끝 4자리)", max_chars=4)
            in_sex = st.radio("성별", ["수", "암"], horizontal=True)
            in_weight = st.number_input("생시 체중 (kg)", value=25.0)
        
        with c2:
            st.info("📷 나중에는 여기에 찍은 사진으로 AI가 자동 식별합니다.")
            in_photo = st.camera_input("송아지 사진 촬영")

        # 제출 버튼
        if st.form_submit_button("등록 하기"):
            if in_mother: # 최소한의 유효성 검사
                new_id = generate_id(in_date, in_mother, in_sex)
                
                # 데이터 구조체 (Dictionary)
                new_data = {
                    "id": new_id,
                    "birth_date": datetime.combine(in_date, datetime.min.time()),
                    "mother": in_mother,
                    "sex": in_sex,
                    "birth_weight": in_weight,
                    "current_weight": in_weight,
                    "photo": in_photo,
                    "colostrum_status": "미급여", # 초기 상태
                    "colostrum_vol": 0
                }
                
                st.session_state.calves_db.append(new_data)
                st.toast(f"✅ {new_id} 등록 완료! 관리 탭에서 확인하세요.")
                st.rerun() # 즉시 리스트 갱신
            else:
                st.error("어미 번호는 필수입니다.")

# =========================================================
# [Tab 2] 통합 관리 (Manage) -> if문 제거하고 match-case 적용
# =========================================================
with tab_manage:
    if current_calf is None:
        st.warning("👈 왼쪽 사이드바에서 송아지를 선택하거나, 신규 등록해주세요.")
    else:
        # [상단 요약 정보]
        adg, days = get_adg(current_calf['birth_weight'], current_calf['current_weight'], current_calf['birth_date'])
        
        # UI 레이아웃
        col_main, col_detail = st.columns([1, 2])
        
        with col_main:
            if current_calf['photo']:
                st.image(current_calf['photo'], caption=current_calf['id'])
            else:
                st.info("등록된 사진 없음")
            
            st.metric("현재 일령", f"{days}일")
            st.metric("일당 증체량(ADG)", f"{adg:.2f} kg", delta_color="normal" if adg > 0.8 else "inverse")

        with col_detail:
            # 서브 탭으로 기능 분리
            sub_t1, sub_t2 = st.tabs(["🍼 초유/성장", "🏥 질병/예방 (Smart Log)"])
            
            # --- 서브탭 1: 초유 및 체중 ---
            with sub_t1:
                st.markdown("#### 초유 급여 관리")
                # [최적화] 라디오 버튼 선택에 따라 UI가 바뀌지만 로직은 심플하게
                c_type = st.radio("급여 방식", ["모유 포유", "분말 초유"], horizontal=True, key="c_type")
                
                # 분말일 때만 입력창 활성화 (조건부 렌더링)
                c_vol = 0
                if c_type == "분말 초유":
                    c_vol = st.number_input("급여량 (ml)", step=50, key="c_vol")
                
                if st.button("초유 정보 업데이트"):
                    current_calf['colostrum_status'] = c_type
                    current_calf['colostrum_vol'] = c_vol
                    st.success("저장됨")

                st.divider()
                st.markdown("#### 체중 갱신")
                new_w = st.number_input("현재 체중 측정값 (kg)", value=current_calf['current_weight'])
                if st.button("체중 저장"):
                    current_calf['current_weight'] = new_w
                    st.rerun()

            # --- 서브탭 2: 질병 관리 (여기가 match-case 핵심) ---
            with sub_t2:
                st.markdown("#### 🏥 스마트 질병 일지")
                
                with st.form("health_log_form"):
                    h_date = st.date_input("날짜", datetime.now())
                    h_type = st.selectbox("기록 유형", ["예방접종", "질병치료", "특이사항"])
                    
                    # -------------------------------------------------
                    # [핵심] Python 3.10 match-case 문법 적용
                    # 복잡한 if-elif 구조를 제거하고 가독성 확보
                    # -------------------------------------------------
                    detail_val = ""
                    
                    match h_type:
                        case "예방접종":
                            # 백신 리스트 (딕셔너리로 관리 추천)
                            vaccines = ["로타/코로나(설사)", "전염성비기관염(호흡기)", "구제역", "BVD"]
                            v_sel = st.selectbox("백신 종류", vaccines)
                            detail_val = f"[백신] {v_sel} 접종"
                            st.caption("💉 접종 이력은 자동으로 스케줄에 반영됩니다.")
                            
                        case "질병치료":
                            # 치료는 증상과 처방이 중요
                            sym = st.text_input("증상", placeholder="예: 설사, 기침")
                            med = st.text_input("처방 약제", placeholder="예: 대성 지속성 지사제 5cc")
                            detail_val = f"[치료] 증상: {sym} | 처방: {med}"
                            
                        case "특이사항":
                            memo = st.text_area("메모", placeholder="활력 저하, 사료 섭취 감소 등")
                            detail_val = f"[관찰] {memo}"
                            
                        case _:
                            detail_val = "기록 없음"
                    
                    # 저장 로직
                    if st.form_submit_button("기록 추가"):
                        log_entry = {
                            "calf_id": current_calf['id'],
                            "date": h_date.strftime("%Y-%m-%d"),
                            "type": h_type,
                            "detail": detail_val
                        }
                        st.session_state.health_logs.append(log_entry)
                        st.success("기록되었습니다.")

                # [최적화] 로그 출력 (List Comprehension으로 필터링)
                my_logs = [l for l in st.session_state.health_logs if l['calf_id'] == current_calf['id']]
                
                if my_logs:
                    st.table(pd.DataFrame(my_logs)[['date', 'type', 'detail']])
                else:
                    st.caption("아직 기록이 없습니다.")
                    