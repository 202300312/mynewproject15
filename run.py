"""모두를 위한 학교 콘서트장 만들기 - Streamlit + SQLite 협업 버전."""
from pathlib import Path
import re
import sqlite3
import streamlit as st
from streamlit.components.v1 import declare_component
from db import (initialize, register, authenticate, userid_exists, group_info,
                create_login_session, restore_login_session, revoke_login_session,
                active_group_detail, group_snapshot, create_group, invite_members,
                respond_invite, leave_group, save_group_patch, is_teacher, remove_member,
                teacher_add_member, teacher_set_owner, teacher_rename_group, teacher_delete_student, teacher_delete_group)

ROOT=Path(__file__).resolve().parent
initialize()
st.set_page_config(page_title="모두를 위한 학교 콘서트장 만들기",page_icon="🌿",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
header[data-testid="stHeader"],footer,[data-testid="stSidebar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stMainBlockContainer"]{max-width:100%!important;padding:0!important;margin:0!important}
[data-testid="stAppViewContainer"]{background:#f6faf6}
[data-testid="stCustomComponent"]{margin:0!important;padding:0!important}
/* The login-restore component is mounted AFTER the login forms. */
[data-testid="stCustomComponent"] iframe{border:0!important;display:block!important}
/* Streamlit sometimes wraps custom components in additional layout layers. */
body:has(.gc-login-title) [data-testid="stCustomComponent"] iframe{height:1px!important;min-height:1px!important;max-height:1px!important;width:1px!important;opacity:0!important;pointer-events:none!important}
body:has(.gc-login-title) [data-testid="stCustomComponent"]{height:1px!important;min-height:1px!important;max-height:1px!important;overflow:hidden!important;margin:0!important;padding:0!important}
body:has(.gc-login-title) [data-testid="stMainBlockContainer"]{padding:12px 24px 24px!important;min-height:0!important;margin:0!important}
body:has(.gc-login-title) [data-testid="stVerticalBlock"]{gap:.5rem!important}
/* Authenticated lesson iframe (single-scrolling content frame). */
body:not(:has(.gc-login-title)) [data-testid="stCustomComponent"] iframe{width:100%!important;height:100dvh!important}
/* 교사 전용 DB 백업 버튼: 스크롤 가능한 iframe 아래에 숨지 않도록 고정 */
.st-key-teacher_db_download{position:fixed!important;right:18px!important;bottom:18px!important;z-index:99999!important;width:auto!important;background:#ffffff!important;padding:6px!important;border-radius:10px!important;box-shadow:0 2px 12px #0002!important}
.st-key-teacher_db_download button{white-space:nowrap!important}
.gc-login-title{font-size:clamp(21px,3vw,39px);font-weight:900;white-space:nowrap;letter-spacing:-1.1px;color:#173525}
.gc-login-sub{font-weight:650;color:#48725a;margin:4px 0 30px}
/* In login mode the 1-pixel token-restore component must not lock page scroll. */
body:has(.gc-login-title){overflow-y:auto!important}
body:has(.gc-login-title) [data-testid="stAppViewContainer"],
body:has(.gc-login-title) [data-testid="stMain"]{overflow-y:auto!important;height:auto!important;min-height:100dvh!important}
body:has(.gc-login-title) [data-testid="stMainBlockContainer"]{margin-top:0!important;transform:none!important}
/* Keep login UI at the TOP and allow normal vertical scrolling. */
body:has(.gc-login-title),body:has(.gc-login-title) [data-testid="stAppViewContainer"],body:has(.gc-login-title) [data-testid="stMain"]{overflow-y:auto!important;height:auto!important;min-height:100dvh!important}
body:not(:has(.gc-login-title)) [data-testid="stAppViewContainer"],body:not(:has(.gc-login-title)) [data-testid="stMain"]{height:100dvh!important;overflow:hidden!important}
@media(prefers-color-scheme:dark){
[data-testid="stAppViewContainer"]{background:#121a16!important;color:#e6eee9!important}
.gc-login-title{color:#ebf9ee!important}.gc-login-sub{color:#b1d2bb!important}
[data-testid="stMainBlockContainer"]{background:#121a16!important}
}
</style>""",unsafe_allow_html=True)

if 'user' not in st.session_state:st.session_state.user=None
if 'group_id' not in st.session_state:st.session_state.group_id=None
if 'last_event_id' not in st.session_state:st.session_state.last_event_id=None
if 'notice' not in st.session_state:st.session_state.notice=None
if 'registered_notice' not in st.session_state:st.session_state.registered_notice=False
if 'auth_token' not in st.session_state:st.session_state.auth_token=None

component = declare_component('concert_collab', path=str(ROOT/'frontend'))

if st.session_state.user is None:
    # 등록 성공 후 다음 실행에서, 입력 위젯을 만들기 *전에* 상태 초기화.
    # 위젯이 생성된 뒤 session_state[key]를 수정하면
    # StreamlitWidgetAlreadyInstantiatedError가 발생할 수 있습니다.
    if st.session_state.pop('clear_registration_fields', False):
        for field in ('new_student_name', 'new_student_id',
                      'new_student_password', 'new_student_confirm'):
            st.session_state.pop(field, None)
    # No top spacer: keep login immediately visible in the viewport.
    _,center,_=st.columns([.08,2.8,.08])
    with center:
        st.markdown('<div class="gc-login-title">🌿 모두를 위한 학교 콘서트장 만들기</div><div class="gc-login-sub">우리는 학교 축제 콘서트장 기획단!</div>',unsafe_allow_html=True)
        lt,rt=st.tabs(['로그인','신규등록'])
        with lt:
            with st.form('login'):
                userid=st.text_input('아이디(학번)')
                passwd=st.text_input('비밀번호',type='password')
                if st.form_submit_button('로그인',use_container_width=True,type='primary'):
                    user=authenticate(userid,passwd)
                    if user:
                        st.session_state.user=user
                        st.session_state.auth_token=create_login_session(user['id_num'])
                        st.session_state.group_id=None
                        st.session_state.last_event_id=None
                        st.rerun()
                    st.error('아이디 또는 비밀번호를 확인하세요.')
        with rt:

            # Streamlit 기본 위젯만 사용합니다. 사용자 정의 컴포넌트 경로에
            # 의존하지 않으므로 클라우드 배포 환경에서도 등록 창이 표시됩니다.
            new_name=st.text_input('이름',key='new_student_name',max_chars=40)
            left,right=st.columns([3,2],vertical_alignment='bottom')
            with left:
                new_id=st.text_input('아이디(학번)',key='new_student_id',max_chars=15,
                                     placeholder='숫자 4~15자리')
            with right:
                if new_id.strip():
                    if not re.fullmatch(r'[0-9]{4,15}',new_id.strip()):
                        st.caption('학번은 숫자 4~15자리로 입력하세요.')
                    elif userid_exists(new_id):
                        st.error('이미 등록된 아이디입니다.',icon='⚠️')
                else:
                    st.caption(' ')
            new_password=st.text_input('비밀번호 (8자 이상)',type='password',
                                       key='new_student_password',max_chars=128)
            password_left,password_right=st.columns([3,2],vertical_alignment='bottom')
            with password_left:
                confirm_password=st.text_input('비밀번호 확인',type='password',
                                               key='new_student_confirm',max_chars=128)
            with password_right:
                if confirm_password:
                    if new_password == confirm_password:
                        st.success('비밀번호가 일치합니다.',icon='✅')
                    else:
                        st.error('비밀번호가 일치하지 않습니다.',icon='⚠️')
                else:
                    st.caption(' ')
            invalid_id=(not re.fullmatch(r'[0-9]{4,15}',new_id.strip()) or
                        userid_exists(new_id) if new_id else True)
            disabled=(not new_name.strip() or invalid_id or
                      len(new_password)<8 or new_password!=confirm_password)
            if st.button('신규등록',key='register_submit',type='primary',
                         use_container_width=True,disabled=disabled):
                ok,msg=register(new_name,new_id,new_password)
                if ok:
                    # 가입 성공 시 바로 로그인합니다. 같은 실행에서 이미 생성된
                    # 위젯의 session_state는 변경하지 않습니다.
                    user=authenticate(new_id,new_password)
                    if user:
                        st.session_state.user=user
                        st.session_state.auth_token=create_login_session(user['id_num'])
                        st.session_state.notice='✅ 회원가입이 완료되었습니다. 자동 로그인되었습니다.'
                        st.session_state.clear_registration_fields=True
                        st.rerun()
                    st.success('회원가입이 완료되었습니다. 로그인해 주세요.')
                else:
                    st.error(msg)
    # 브라우저 새로고침 후 Streamlit 세션이 초기화되어도
    # 브라우저에 남아 있는 만료 가능한 토큰으로 로그인 상태를 복원합니다.
    restore_result = component(mode='restore', key='concert_auth_restore', default=None, height=1)
    if isinstance(restore_result,dict) and restore_result.get('type')=='restore':
        restored = restore_login_session(restore_result.get('token',''))
        if restored:
            st.session_state.user=restored
            st.session_state.auth_token=restore_result.get('token')
            st.rerun()
    st.stop()

me=st.session_state.user
# 이미 소속된 모둠이 있으면 로그인 직후 해당 공동 기록을 바로 사용합니다.
my_groups=group_info(me['id_num'])['groups']
if my_groups:
    if st.session_state.group_id not in [g['id'] for g in my_groups]:
        st.session_state.group_id=my_groups[0]['id']
else:
    st.session_state.group_id=None
if st.session_state.notice:
    st.toast(st.session_state.notice, icon='✅')
    st.session_state.notice=None

@st.fragment(run_every='3s')
def lesson():
    me=st.session_state.user
    gid=st.session_state.group_id
    detail=active_group_detail(me['id_num'],gid) if gid else None
    if gid and detail is None:
        st.session_state.group_id=None;gid=None
    info=group_info(me['id_num'])
    info['isTeacher']=me.get('role')=='teacher'
    info['activeGroup']=detail
    if gid:
        snapshot,version=group_snapshot(me['id_num'],gid)
        context='group:'+str(gid)
    else:
        # 모둠에 가입하기 전에는 개인 학습 기록을 제공하지 않습니다.
        snapshot,version={},0
        context='onboarding'
    result=component(user=me['userid'],context=context,snapshot=snapshot,version=version,
        groupInfo=info,authToken=st.session_state.auth_token,mode='lesson',
        key='school_concert_'+str(me['id_num']),default=None,height=850)
    if not isinstance(result,dict):return
    event_id=result.get('event_id')
    if event_id==st.session_state.last_event_id:return
    st.session_state.last_event_id=event_id
    kind=result.get('type')
    try:
        if kind=='logout':
            if result.get('context')==context and result.get('patch'):
                if gid:save_group_patch(me['id_num'],gid,result['patch'])
                # 미가입 상태는 개인 기록을 저장하지 않습니다.
            revoke_login_session(st.session_state.auth_token)
            st.session_state.auth_token=None
            st.session_state.user=None;st.session_state.group_id=None
            st.rerun(scope='app')
        elif kind=='save':
            if result.get('context')!=context:return
            patch=result.get('patch',{})
            if gid:save_group_patch(me['id_num'],gid,patch)
            # 미가입 상태는 학습 기록을 저장하지 않습니다.
        elif kind=='group_action':
            if result.get('context')==context and result.get('patch'):
                if gid:save_group_patch(me['id_num'],gid,result['patch'])
                # 미가입 상태는 개인 기록을 저장하지 않습니다.
            action=result.get('action');d=result.get('detail') or {}
            if action=='create':
                if me.get('role')=='teacher':raise ValueError('교사 계정은 기존 모둠을 관리합니다.')
                st.session_state.group_id=create_group(me['id_num'],d.get('name',''),d.get('members',[]),'')
            elif action=='switch':
                proposed=d.get('group_id')
                if not proposed or not active_group_detail(me['id_num'],int(proposed)):
                    raise ValueError('참여 중인 모둠만 선택할 수 있습니다.')
                st.session_state.group_id=int(proposed)
            elif action=='refresh_members':
                # The next fragment render reads the latest registered users from SQLite.
                pass
            elif action=='invite':
                if not gid:raise ValueError('모둠을 먼저 선택하세요.')
                invite_members(me['id_num'],gid,d.get('members',[]))
            elif action=='accept':
                respond_invite(me['id_num'],int(d['group_id']),True)
                st.session_state.group_id=int(d['group_id'])
            elif action=='decline':respond_invite(me['id_num'],int(d['group_id']),False)
            elif action=='kick':
                if not gid:raise ValueError('모둠을 선택하세요.')
                remove_member(me['id_num'],gid,int(d['user_id']))
            elif action=='teacher_add':
                if not gid:raise ValueError('모둠을 선택하세요.')
                teacher_add_member(me['id_num'],gid,int(d['user_id']))
            elif action=='teacher_owner':
                if not gid:raise ValueError('모둠을 선택하세요.')
                teacher_set_owner(me['id_num'],gid,int(d['user_id']))
            elif action=='teacher_delete_student':
                target_id=int(d['user_id'])
                # UI requires student-id confirmation; server independently verifies it.
                confirmed_id=str(d.get('confirm_userid','')).strip()
                with sqlite3.connect(__import__('db').DB_PATH) as verify_db:
                    row=verify_db.execute("SELECT userid FROM users WHERE id_num=? AND role='student'",(target_id,)).fetchone()
                if not row or row[0]!=confirmed_id:
                    raise ValueError('삭제하려는 학생의 학번이 일치하지 않습니다.')
                st.toast(teacher_delete_student(me['id_num'],target_id), icon='✅')
            elif action=='teacher_delete_group':
                if not gid:raise ValueError('모둠을 먼저 선택하세요.')
                confirmation=str(d.get('confirm_name',''))
                st.toast(teacher_delete_group(me['id_num'],gid,confirmation),icon='✅')
                st.session_state.group_id=None
            elif action=='teacher_rename':
                if not gid:raise ValueError('모둠을 선택하세요.')
                teacher_rename_group(me['id_num'],gid,d['name'])
            elif action=='leave':
                if not gid:raise ValueError('선택한 모둠이 없습니다.')
                leave_group(me['id_num'],gid)
                st.session_state.group_id=None
            st.rerun(scope='fragment')
    except (ValueError, KeyError, TypeError, sqlite3.IntegrityError) as e:
        st.error('처리할 수 없습니다: '+str(e))

lesson()

# 교사 전용 실제 운영 DB 백업. SQLite 온라인 백업 API로 일관된 스냅샷을 생성합니다.
if st.session_state.user and st.session_state.user.get('role') == 'teacher':
    from db import DB_PATH
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        snapshot_path=Path(tmp_dir)/'concert_school_new.db'
        with sqlite3.connect(DB_PATH, timeout=20) as source, sqlite3.connect(snapshot_path) as target:
            source.backup(target)
        db_bytes=snapshot_path.read_bytes()
    st.download_button(
        '⬇ 운영 중인 SQLite DB 다운로드 (교사용)', data=db_bytes,
        file_name='concert_school_new.db', mime='application/vnd.sqlite3',
        key='teacher_db_download', on_click='ignore'
    )
