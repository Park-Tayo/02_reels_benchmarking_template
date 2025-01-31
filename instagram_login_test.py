import streamlit as st
import instaloader
import os
from pathlib import Path
from dotenv import load_dotenv

def test_instagram_login():
    st.title("Instagram 로그인 테스트")
    
    # .env 파일 로드
    load_dotenv()
    
    # 현재 환경 변수 값 표시
    current_username = os.getenv("INSTAGRAM_USERNAME", "")
    
    with st.form("instagram_login"):
        st.write("### Instagram 로그인 정보 입력")
        username = st.text_input("사용자명:", value=current_username)
        password = st.text_input("비밀번호:", type="password")
        submit = st.form_submit_button("로그인 테스트")
        
        if submit:
            if not username or not password:
                st.error("사용자명과 비밀번호를 모두 입력해주세요.")
                return
                
            try:
                # Instaloader 인스턴스 생성
                L = instaloader.Instaloader(
                    max_connection_attempts=3,
                    download_videos=False,
                    download_geotags=False,
                    download_comments=False,
                    download_pictures=False,
                    compress_json=False,
                    save_metadata=False,
                    quiet=True
                )
                
                # 세션 파일 경로
                session_file = f"{username}_instagram_session"
                
                # 기존 세션 파일 삭제 (새로운 테스트를 위해)
                if os.path.exists(session_file):
                    os.remove(session_file)
                    st.info("기존 세션 파일을 삭제했습니다.")
                
                # 로그인 시도
                st.info("로그인 시도 중...")
                L.login(username, password)
                
                # 로그인 성공 시 세션 저장
                L.save_session_to_file(session_file)
                
                # 프로필 정보 가져와서 테스트
                profile = instaloader.Profile.from_username(L.context, username)
                
                # 성공 메시지와 함께 프로필 정보 표시
                st.success("로그인 성공! ✅")
                st.write("### 프로필 정보")
                st.write(f"- 사용자명: {profile.username}")
                st.write(f"- 팔로워 수: {profile.followers}")
                st.write(f"- 팔로잉 수: {profile.followees}")
                
                # 환경 변수 업데이트
                env_path = Path('.env')
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        username_updated = False
                        password_updated = False
                        for line in lines:
                            if line.startswith('INSTAGRAM_USERNAME='):
                                f.write(f'INSTAGRAM_USERNAME={username}\n')
                                username_updated = True
                            elif line.startswith('INSTAGRAM_PASSWORD='):
                                f.write(f'INSTAGRAM_PASSWORD={password}\n')
                                password_updated = True
                            else:
                                f.write(line)
                        
                        if not username_updated:
                            f.write(f'INSTAGRAM_USERNAME={username}\n')
                        if not password_updated:
                            f.write(f'INSTAGRAM_PASSWORD={password}\n')
                    
                    st.success(".env 파일이 업데이트되었습니다.")
                else:
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.write(f'INSTAGRAM_USERNAME={username}\n')
                        f.write(f'INSTAGRAM_PASSWORD={password}\n')
                    st.success(".env 파일이 생성되었습니다.")
                
            except instaloader.exceptions.BadCredentialsException:
                st.error("로그인 실패: 잘못된 사용자명 또는 비밀번호입니다.")
            except instaloader.exceptions.TwoFactorAuthRequiredException:
                st.error("2단계 인증이 필요합니다. 2단계 인증을 비활성화하거나 다른 계정을 사용해주세요.")
            except instaloader.exceptions.ConnectionException as e:
                st.error(f"연결 오류: {str(e)}")
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                st.error("상세 오류 정보:", exc_info=True)

if __name__ == "__main__":
    test_instagram_login() 