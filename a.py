import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 초기 설정 및 딕셔너리 매핑
# ---------------------------------------------------------
st.set_page_config(page_title="Hanwoo Calf Manager V17", layout="wide")

# 성별 따른 상태 옵션 매핑
STATUS_OPTIONS_MAP = {
    "수": ["사육중", "송아지 판매", "비육", "KPN 선발", "폐사"],
    "암": ["사육중", "송아지 판매", "비육", "대체우 선발", "폐사"],
    "미정": ["사육중", "폐사"],
    "미상": ["사육중", "폐사"]
}

# UI 렌더링 핸들러 매핑 (Dictionary Dispatcher)
def ui_vaccine(k): return f"[백신] {st.selectbox('백신', st.session_state.vaccine_list, key=f'v_{k}')}"
def ui_treat(k): return f"[치료] {st.text_input('증상', key=f's_{k}')} :: {st.text_input('약제', key=f'm_{k}')}"
def ui_feces(k): return f"[분변] {st.selectbox('상태', ['정상', '묽은변', '설사', '혈변'], key=f'f_{k}')}"
def ui_disease(k): return f"[질병] {st.text_input('병명', key=f'd_{k}')} ({st.selectbox('상태', ['의심','치료중','회복'], key=f'ds_{k}')})"
def ui_memo(k): return f"[메모] {st.text_input('내용', key=f'mm_{k}')}"

LOG_UI_MAP = {
    "예방접종": ui_vaccine, "질병치료": ui_treat,
    "분변관찰": ui_feces, "질병/장애": ui_disease, "특이사항": ui_memo
}

# 세션 상태 초기화
DEFAULT_STATE = {
    'calves_db': [], 'health_logs': [],
    'vaccine_list': ["로타/코로나", "비기관염", "구제역", "BVD", "비타민ADE"],
    'target_calf_id': None, 'current_view': "전체 목록"
}
for k, v in DEFAULT_STATE.items(): st.session_state.setdefault(k, v)

# ---------------------------------------------------------
# 2. 핵심 로직 함수
# ---------------------------------------------------------
def get_latest_weight_info(calf):
    """최신 체중 계산: 생시 -> 이유 -> 정기측정(날짜순)"""
    records = [{'date': calf['birth_date'], 'weight': calf['birth_weight'], 'src': '생시'}]
    
    if calf.get('weaning'):
        w_date = datetime.strptime(calf['weaning']['date'], "%Y-%m-%d")
        records.append({'date': w_date, 'weight': calf['weaning']['weight'], 'src': '이유후'})

    for pw in calf.get('periodic_weights', []):
        p_date = datetime.strptime(pw['date'], "%Y-%m-%d")
        records.append({'date': p_date, 'weight': pw['weight'], 'src': '정기측정'})

    records.sort(key=lambda x: x['date'], reverse=True)
    return records[0]

def generate_id(date_obj, mother, sex, db):
    d_str = date_obj.strftime('%y%m%d')
    m_str = mother.strip() if mother.strip() else "미상"
    s_str = sex if sex else "미정"
    base = f"{d_str}-{m_str}-{s_str}"
    seq = sum(1 for c in db if c['id'].startswith(base)) + 1
    return f"{base}-{seq:02d}"

def change_view(view, calf_id=None):
    st.session_state.current_view = view
    if calf_id: st.session_state.target_calf_id = calf_id
    st.rerun()

# ---------------------------------------------------------
# 3. 화면별 함수 (View Functions)
# ---------------------------------------------------------
def view_list():
    st.subheader("보유 송아지 현황")

    # 검색 필터
    c1, c2, c3 = st.columns([1, 1, 2])
    s_date = c1.date_input("출생일", value=None)
    s_text = c2.text_input("번호 검색")
    all_stat = sorted(list(set(sum(STATUS_OPTIONS_MAP.values(), []))))
    s_stat = c3.multiselect("상태 필터", all_stat)

    filtered = [
        c for c in st.session_state.calves_db
        if (not s_date or c['birth_date'].date() == s_date) and
           (not s_text or s_text in c['id'] or s_text in c['mother']) and
           (not s_stat or c.get('status', '사육중') in s_stat)
    ]

    st.info(f"전체: {len(st.session_state.calves_db)}두 / 검색: {len(filtered)}두")

    for calf in reversed(filtered):
        days = (datetime.now() - calf['birth_date']).days
        w_info = get_latest_weight_info(calf)
        
        # [수정 사항] 이유 상태 텍스트 결정
        match bool(calf.get('weaning')):
            case True: wean_status = "이유 완료"
            case False: wean_status = "포유 중"

        with st.expander(f"{calf['id']} ({calf.get('status', '사육중')} / {wean_status} / {w_info['weight']}kg)"):
            ec1, ec2 = st.columns([1, 2])
            with ec1:
                if calf['photo']: st.image(calf['photo'])
                st.write(f"상태: {calf.get('status', '사육중')}")
                st.write(f"이유상태: {wean_status}")
                if st.button("수정 및 관리", key=f"btn_{calf['id']}"):
                    change_view("정밀 관리", calf['id'])

            with ec2:
                t_info, t_hist = st.tabs(["기본 정보", "기록 이력"])
                with t_info:
                    st.write(f"출생: {calf['birth_date'].strftime('%Y-%m-%d')} | 어미: {calf['mother']}")
                    st.write(f"성별: {calf['sex']} | 생시: {calf['birth_weight']}kg")
                    if calf.get('weaning'):
                        st.write(f"이유정보: {calf['weaning']['date']} ({calf['weaning']['weight']}kg)")
                    st.caption(f"건강: {calf.get('disease_status','정상')} / 분변: {calf.get('feces_state','정상')}")
                
                with t_hist:
                    if calf.get('periodic_weights'):
                        st.dataframe(pd.DataFrame(calf['periodic_weights']), hide_index=True)
                    logs = [l for l in st.session_state.health_logs if l['id'] == calf['id']]
                    if logs:
                        logs.sort(key=lambda x: x['timestamp'], reverse=True)
                        st.dataframe(pd.DataFrame(logs)[['date', 'type', 'detail']], hide_index=True)

def view_register():
    st.subheader("신규 개체 등록")
    rc1, rc2 = st.columns(2)
    with rc1:
        in_date = st.date_input("출생일", datetime.now())
        in_mother = st.text_input("어미번호", max_chars=4)
        in_sex = st.radio("성별", ["수", "암", "미정"], horizontal=True)
        in_weight = st.number_input("생시체중", value=25.0)
    with rc2:
        in_photo = st.camera_input("촬영")

    st.divider()
    cc1, cc2 = st.columns(2)
    with cc1:
        in_navel = st.checkbox("배꼽 소독", value=True)
        in_col_type = st.radio("초유", ["미급여", "모유", "분말"], horizontal=True)
        in_col_vol = st.number_input("분말량", step=50) if in_col_type == "분말" else 0
    with cc2:
        do_init = st.checkbox("초기 처치 기록")
        i_type, i_detail = "기록없음", ""
        if do_init:
            sel_t = st.selectbox("유형", list(LOG_UI_MAP.keys()), key="reg_type")
            i_type = sel_t
            i_detail = LOG_UI_MAP[sel_t]("reg")

    if st.button("등록 완료", type="primary"):
        if not in_mother.strip() and not in_photo:
            st.error("어미번호 또는 사진 필수")
        else:
            new_id = generate_id(in_date, in_mother, in_sex, st.session_state.calves_db)
            st.session_state.calves_db.append({
                "id": new_id, "official_id": None,
                "birth_date": datetime.combine(in_date, datetime.now().time()),
                "mother": in_mother if in_mother else "미상",
                "sex": in_sex, "birth_weight": in_weight,
                "current_weight": in_weight, "photo": in_photo, "navel_disinfect": in_navel,
                "colostrum": {"type": in_col_type, "vol": in_col_vol},
                "status": "사육중", "feces_state": "정상", "disease_status": "정상",
                "weaning": None, "periodic_weights": []
            })
            if do_init:
                st.session_state.health_logs.append({
                    "id": new_id, "timestamp": datetime.now(),
                    "date": in_date.strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M"),
                    "type": i_type, "detail": i_detail
                })
            st.success(f"등록됨: {new_id}")

def view_manage():
    all_ids = [c['id'] for c in st.session_state.calves_db]
    try: idx = all_ids.index(st.session_state.target_calf_id)
    except: idx = 0
    
    sel_id = st.selectbox("관리 대상", all_ids, index=idx if all_ids else 0)
    cur_calf = next((c for c in st.session_state.calves_db if c['id'] == sel_id), None)
    if not cur_calf: return

    st.markdown(f"### 관리: {cur_calf['id']}")
    
    # 상태 변경
    status_opts = STATUS_OPTIONS_MAP.get(cur_calf['sex'], ["사육중"])
    try: s_idx = status_opts.index(cur_calf.get('status', '사육중'))
    except: s_idx = 0
    new_status = st.selectbox("개체 상태 변경", status_opts, index=s_idx)
    cur_calf['status'] = new_status

    tab_b, tab_g, tab_h = st.tabs(["기본 정보", "성장(체중)", "건강(질병)"])

    with tab_b:
        bc1, bc2 = st.columns([1, 2])
        with bc1:
            if cur_calf['photo']: st.image(cur_calf['photo'])
            st.write(f"생시체중: {cur_calf['birth_weight']}kg")
            st.write(f"배꼽소독: {'완료' if cur_calf.get('navel_disinfect') else '미실시'}")
            
        with bc2:
            st.markdown("#### 상태 및 정보 수정")
            f_opts = ["정상", "묽은변", "설사(수양성)", "혈변", "변비"]
            curr_f = cur_calf.get('feces_state', '정상')
            new_feces = st.selectbox("분변 상태", f_opts, index=f_opts.index(curr_f) if curr_f in f_opts else 0)
            new_disease = st.text_input("질병/장애 상태", value=cur_calf.get('disease_status', '정상'))
            if st.button("상태 저장"):
                cur_calf['feces_state'] = new_feces
                cur_calf['disease_status'] = new_disease
                st.success("저장됨")

            st.divider()
            oid = cur_calf['official_id'] if cur_calf['official_id'] else ""
            new_oid = st.text_input("이력번호(12자리)", value=oid, max_chars=12)
            if st.button("이력번호 저장"): cur_calf['official_id'] = new_oid

    with tab_g:
        gc1, gc2 = st.columns(2)
        with gc1:
            if cur_calf.get('weaning'):
                st.success(f"이유 완료: {cur_calf['weaning']['date']} ({cur_calf['weaning']['weight']}kg)")
                if st.button("이유 취소"): cur_calf['weaning'] = None; st.rerun()
            else:
                wd = st.date_input("이유일", datetime.now())
                ww = st.number_input("이유체중", value=cur_calf['current_weight'])
                if st.button("이유 처리"): cur_calf['weaning'] = {"date": wd.strftime("%Y-%m-%d"), "weight": ww}; st.rerun()
        with gc2:
            pd_date = st.date_input("측정일", datetime.now())
            pd_w = st.number_input("측정값", value=cur_calf['current_weight'])
            if st.button("기록 추가"):
                if 'periodic_weights' not in cur_calf: cur_calf['periodic_weights'] = []
                cur_calf['periodic_weights'].append({"date": pd_date.strftime("%Y-%m-%d"), "weight": pd_w})
                st.success("추가됨")

    with tab_h:
        # [수정 사항] 시간 입력 방식 개선 (현재 시간 기본 + 자유 입력)
        with st.form("log"):
            c1, c2 = st.columns(2)
            ld = c1.date_input("날짜", datetime.now())
            lt = c2.time_input("시간 (24h 기준)", datetime.now().time()) # 현재 시간 자동 표시 및 직접 입력
            
            l_type = st.selectbox("유형", list(LOG_UI_MAP.keys()))
            l_detail = LOG_UI_MAP[l_type]("mng")
            
            if st.form_submit_button("저장"):
                st.session_state.health_logs.append({
                    "id": cur_calf['id'],
                    "timestamp": datetime.combine(ld, lt),
                    "date": ld.strftime("%Y-%m-%d"), "time": lt.strftime("%H:%M"),
                    "type": l_type, "detail": l_detail
                })
                if l_type == "분변관찰": cur_calf['feces_state'] = l_detail.split("] ")[1]
                if l_type == "질병/장애": cur_calf['disease_status'] = l_detail.split("] ")[1]
                st.success("저장됨")

        logs = [l for l in st.session_state.health_logs if l['id'] == cur_calf['id']]
        if logs:
            logs.sort(key=lambda x: x['timestamp'], reverse=True)
            st.dataframe(pd.DataFrame(logs)[['date', 'time', 'type', 'detail']], hide_index=True)

# ---------------------------------------------------------
# 4. 메인 실행 루프
# ---------------------------------------------------------
st.title("한우 송아지 통합 관리 시스템")
menus = ["전체 목록", "신규 등록", "정밀 관리"]
sel = st.radio("메뉴", menus, index=menus.index(st.session_state.current_view), horizontal=True, label_visibility="collapsed")

if sel != st.session_state.current_view:
    st.session_state.current_view = sel
    st.rerun()

st.markdown("---")

match st.session_state.current_view:
    case "전체 목록": view_list()
    case "신규 등록": view_register()
    case "정밀 관리": view_manage()
    
