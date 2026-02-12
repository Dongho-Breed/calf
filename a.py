import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. Config & Data Initialization (Dictionary based)
# ---------------------------------------------------------
st.set_page_config(page_title="Hanwoo Calf Manager Refactored", layout="wide")

# [Refactor] 세션 초기값을 딕셔너리로 관리하여 반복 제거
DEFAULT_STATES = {
    'calves_db': [],
    'health_logs': [],
    'vaccine_list': ["로타/코로나(설사)", "전염성비기관염(호흡기)", "구제역", "BVD", "비타민ADE"],
    'target_calf_id': None,
    'current_view': "전체 목록"
}

for key, default_val in DEFAULT_STATES.items():
    st.session_state.setdefault(key, default_val)

# ---------------------------------------------------------
# 2. Helper Functions & UI Components
# ---------------------------------------------------------
def generate_id(date_obj, mother, sex, db):
    """ID 생성 로직"""
    d_str = date_obj.strftime('%y%m%d')
    m_str = mother.strip() if mother.strip() else "미상"
    s_str = sex if sex else "미정"
    base = f"{d_str}-{m_str}-{s_str}"
    seq = sum(1 for c in db if c['id'].startswith(base)) + 1
    return f"{base}-{seq:02d}"

def change_view(view, calf_id=None):
    """화면 전환"""
    st.session_state.current_view = view
    if calf_id: st.session_state.target_calf_id = calf_id
    st.rerun()

def render_vaccine_manager(key_suffix):
    """[Component] 백신/약품 추가 Expander (중복 제거)"""
    with st.expander("백신/약품 목록 설정 (새 항목 추가)"):
        c1, c2 = st.columns([3, 1])
        new_item = c1.text_input("새 약품명", key=f"new_vac_{key_suffix}")
        if c2.button("추가", key=f"add_vac_{key_suffix}"):
            if new_item and new_item not in st.session_state.vaccine_list:
                st.session_state.vaccine_list.append(new_item)
                st.success(f"'{new_item}' 추가됨")
        st.write("현재 목록:", st.session_state.vaccine_list)

# ---------------------------------------------------------
# 3. Dictionary Dispatcher for Health Inputs
# ---------------------------------------------------------
# [Refactor] 입력 UI 로직을 함수로 분리
def ui_vaccine(key):
    v = st.selectbox("백신 선택", st.session_state.vaccine_list, key=f"vac_{key}")
    return f"[백신/접종] {v}"

def ui_treatment(key):
    sym = st.text_input("증상", key=f"sym_{key}")
    med = st.text_input("사용 약제", key=f"med_{key}")
    return f"[치료] {sym} :: {med}"

def ui_memo(key):
    mem = st.text_input("메모", key=f"mem_{key}")
    return f"[메모] {mem}"

# [Refactor] 유형별 핸들러 매핑 (Dictionary Dispatcher)
LOG_UI_HANDLERS = {
    "예방접종": ui_vaccine,
    "질병치료": ui_treatment,
    "특이사항": ui_memo,
    "영양제": lambda k: f"[영양제] {st.text_input('약품명', value='비타민ADE', key=f'vit_{k}')}"
}

def render_health_inputs(key_prefix):
    """유형 선택 및 상세 입력 UI 생성"""
    l_type = st.selectbox("유형", list(LOG_UI_HANDLERS.keys()), key=f"type_{key_prefix}")
    # 딕셔너리에서 함수를 찾아 실행 (Match-Case 대체 효과)
    handler = LOG_UI_HANDLERS.get(l_type, ui_memo) 
    detail = handler(key_prefix)
    return l_type, detail

# ---------------------------------------------------------
# 4. View Functions (Match-Case Implementation)
# ---------------------------------------------------------
def view_list():
    st.subheader("보유 송아지 현황")
    
    # 검색
    c1, c2 = st.columns(2)
    s_date = c1.date_input("출생일 검색", value=None)
    s_text = c2.text_input("개체/어미 검색")

    # 필터링
    filtered = [
        c for c in st.session_state.calves_db
        if (not s_date or c['birth_date'].date() == s_date) and
           (not s_text or s_text in c['id'] or s_text in c['mother'])
    ]

    st.info(f"전체: {len(st.session_state.calves_db)}두 / 검색결과: {len(filtered)}두")

    if not filtered:
        st.warning("데이터가 없습니다.")
        return

    for calf in reversed(filtered):
        days = (datetime.now() - calf['birth_date']).days
        
        # [Refactor] 상태 배지 Match-Case
        match (days > 30, bool(calf['official_id'])):
            case (True, False): status = "[신고지연]"
            case (True, True): status = "[등록완료]"
            case _: status = "[인큐베이터]"

        with st.expander(f"{status} {calf['id']} (생후 {days}일)"):
            c1, c2, c3 = st.columns([1, 2, 1])
            if calf['photo']: c1.image(calf['photo'])
            else: c1.write("사진 없음")
            
            c2.write(f"출생: {calf['birth_date'].strftime('%Y-%m-%d')} | 어미: {calf['mother']}")
            c2.write(f"성별: {calf['sex']} | 체중: {calf['current_weight']}kg")
            c2.write(f"배꼽소독: {'완료' if calf.get('navel_disinfect') else '미실시'}")
            
            logs = [l for l in st.session_state.health_logs if l['id'] == calf['id']]
            if logs: c2.caption(f"최근: {logs[-1]['date']} {logs[-1]['type']}")

            if c3.button("수정 및 관리", key=f"btn_{calf['id']}"):
                change_view("정밀 관리", calf['id'])

def view_register():
    st.subheader("신규 개체 등록")
    st.caption("어미 번호 또는 사진 필수")

    c1, c2 = st.columns(2)
    in_date = c1.date_input("출생일", datetime.now())
    in_mother = c1.text_input("어미번호(4자리)", max_chars=4)
    in_sex = c1.radio("성별", ["수", "암", "미정"], horizontal=True)
    in_weight = c1.number_input("생시체중", value=25.0)
    in_photo = c2.camera_input("촬영")

    st.divider()
    st.markdown("##### 초기 처치")
    
    cc1, cc2 = st.columns(2)
    in_navel = cc1.checkbox("배꼽 소독 완료", value=True)
    in_col_type = cc1.radio("초유", ["미급여", "모유", "분말"], horizontal=True)
    in_col_vol = cc1.number_input("분말량(ml)", step=50) if in_col_type == "분말" else 0

    with cc2:
        do_init = st.checkbox("초기 약품 투여 기록")
        init_type, init_detail = "기록없음", ""
        if do_init:
            # [Reuse] 재사용 가능한 입력 컴포넌트 호출
            init_type, init_detail = render_health_inputs("reg_init")

    st.markdown("---")
    if st.button("등록 완료", type="primary"):
        if not in_mother.strip() and not in_photo:
            st.error("등록 불가: 어미 번호 또는 사진이 필요합니다.")
        else:
            new_id = generate_id(in_date, in_mother, in_sex, st.session_state.calves_db)
            st.session_state.calves_db.append({
                "id": new_id, "official_id": None,
                "birth_date": datetime.combine(in_date, datetime.now().time()),
                "mother": in_mother if in_mother else "미상",
                "sex": in_sex, "birth_weight": in_weight, "current_weight": in_weight,
                "photo": in_photo, "navel_disinfect": in_navel,
                "colostrum": {"type": in_col_type, "vol": in_col_vol}
            })
            
            if do_init:
                st.session_state.health_logs.append({
                    "id": new_id, "timestamp": datetime.now(),
                    "date": in_date.strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M"),
                    "type": init_type, "detail": init_detail
                })
            st.success(f"등록됨: {new_id}")

    st.divider()
    render_vaccine_manager("reg") # [Reuse] 컴포넌트 재사용

def view_manage():
    # 대상 선택 로직
    all_ids = [c['id'] for c in st.session_state.calves_db]
    try: idx = all_ids.index(st.session_state.target_calf_id)
    except: idx = 0
    
    sel_id = st.selectbox("관리 대상", all_ids, index=idx if all_ids else 0)
    cur_calf = next((c for c in st.session_state.calves_db if c['id'] == sel_id), None)

    if not cur_calf:
        st.warning("데이터 없음")
        return

    st.markdown(f"### 관리 중: {cur_calf['id']}")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        if cur_calf['photo']: st.image(cur_calf['photo'])
        
        # 정보 수정
        cur_calf['current_weight'] = st.number_input("체중 수정", value=cur_calf['current_weight'])
        cur_calf['navel_disinfect'] = st.checkbox("배꼽 소독", value=cur_calf.get('navel_disinfect', False))
        if st.button("저장", key="save_basic"): st.success("저장됨")
        
        st.divider()
        if not cur_calf['official_id']:
            off_id = st.text_input("이력번호")
            if st.button("번호 등록"): 
                cur_calf['official_id'] = off_id
                st.rerun()
        else:
            st.info(f"이력번호: {cur_calf['official_id']}")

    with c2:
        st.markdown("#### 질병/처치 기록")
        with st.form("log_form"):
            fc1, fc2 = st.columns(2)
            l_date = fc1.date_input("날짜", datetime.now())
            l_time = fc2.time_input("시간", datetime.now())
            
            # [Reuse] 재사용 가능한 입력 컴포넌트 호출
            l_type, l_detail = render_health_inputs("mng_log")

            if st.form_submit_button("기록 저장"):
                st.session_state.health_logs.append({
                    "id": cur_calf['id'],
                    "timestamp": datetime.combine(l_date, l_time),
                    "date": l_date.strftime("%Y-%m-%d"),
                    "time": l_time.strftime("%H:%M"),
                    "type": l_type, "detail": l_detail
                })
                st.success("기록됨")
        
        # 로그 테이블
        logs = [l for l in st.session_state.health_logs if l['id'] == cur_calf['id']]
        if logs:
            logs.sort(key=lambda x: x['timestamp'], reverse=True)
            st.table(pd.DataFrame(logs)[['date', 'time', 'type', 'detail']])

    st.divider()
    render_vaccine_manager("mng") # [Reuse] 컴포넌트 재사용

# ---------------------------------------------------------
# 5. Main Execution (View Dispatcher)
# ---------------------------------------------------------
st.title("한우 송아지 통합 관리 시스템")

# 네비게이션
menus = ["전체 목록", "신규 등록", "정밀 관리"]
cur_idx = menus.index(st.session_state.current_view) if st.session_state.current_view in menus else 0
sel_menu = st.radio("메뉴", menus, index=cur_idx, horizontal=True, label_visibility="collapsed")

if sel_menu != st.session_state.current_view:
    st.session_state.current_view = sel_menu
    st.rerun()

st.markdown("---")

# [Refactor] 최우선 요청사항: Match-Case를 사용한 화면 전환
match st.session_state.current_view:
    case "전체 목록": view_list()
    case "신규 등록": view_register()
    case "정밀 관리": view_manage()
    
