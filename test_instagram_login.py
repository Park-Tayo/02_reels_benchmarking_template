import streamlit as st
import instaloader
import os
from dotenv import load_dotenv
import base64
from pathlib import Path
import tempfile

def test_instagram_login():
    st.title("🔒 Instagram 로그인 테스트")
    
    # .env 파일 로드
    load_dotenv()
    
    # 환경 변수 확인
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    INSTAGRAM_SESSION = st.secrets.get("INSTAGRAM_SESSION", "")  # Streamlit Cloud의 secrets에서 가져오기
    
    # 임시 디렉토리 경로 표시
    st.write(f"🗂️ 임시 디렉토리 경로: {tempfile.gettempdir()}")
    st.write(f"💻 현재 운영체제: {os.name}")
    
    # 환경 변수 상태 표시
    st.write("## 📋 환경 변수 상태")
    st.write(f"- USERNAME 설정됨: {'✅' if INSTAGRAM_USERNAME else '❌'}")
    st.write(f"- PASSWORD 설정됨: {'✅' if INSTAGRAM_PASSWORD else '❌'}")
    st.write(f"- SESSION 설정됨: {'✅' if INSTAGRAM_SESSION else '❌'}")
    
    if st.button("🔑 로그인 테스트"):
        try:
            with st.spinner("로그인 시도 중..."):
                # Instaloader 인스턴스 생성
                L = instaloader.Instaloader(
                    max_connection_attempts=1,
                    download_videos=False,
                    download_geotags=False,
                    download_comments=False,
                    download_pictures=False,
                    compress_json=False,
                    save_metadata=False
                )
                
                # 임시 세션 파일 경로
                temp_session_file = Path(tempfile.gettempdir()) / f"{INSTAGRAM_USERNAME}_instagram_session"
                st.write(f"📁 세션 파일 경로: {temp_session_file}")
                
                # 세션 파일이 있으면 삭제
                if temp_session_file.exists():
                    temp_session_file.unlink()
                    st.write("🗑️ 기존 세션 파일 삭제됨")
                
                # 세션 데이터가 있는 경우
                if INSTAGRAM_SESSION:
                    st.write("💾 저장된 세션으로 로그인 시도...")
                    try:
                        # Base64 디코딩 및 세션 파일 생성
                        decoded_session = base64.b64decode(INSTAGRAM_SESSION)
                        temp_session_file.write_bytes(decoded_session)
                        
                        # 세션 로드 시도
                        L.load_session_from_file(INSTAGRAM_USERNAME, str(temp_session_file))
                        
                        # 세션 유효성 검증
                        test_profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
                        st.success("✅ 세션을 사용한 로그인 성공!")
                        return
                        
                    except Exception as e:
                        st.warning(f"⚠️ 세션 로그인 실패: {str(e)}")
                        st.write("🔄 일반 로그인 시도...")
                
                # 일반 로그인 시도
                L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                
                # 로그인 성공 확인
                test_profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
                
                # 새 세션 파일 저장
                L.save_session_to_file(str(temp_session_file))
                
                # 세션 파일을 Base64로 인코딩
                with open(temp_session_file, 'rb') as f:
                    session_data = base64.b64encode(f.read()).decode('utf-8')
                
                st.success("✅ 로그인 성공!")
                st.info("📋 새로운 세션 데이터 (Streamlit Secrets에 저장하세요):")
                st.code(session_data)
                
        except instaloader.exceptions.BadCredentialsException:
            st.error("❌ 로그인 실패: 잘못된 사용자 이름 또는 비밀번호")
        except instaloader.exceptions.ConnectionException as e:
            st.error(f"❌ 연결 오류: {str(e)}")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            st.error("❌ 2단계 인증이 필요합니다")
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류: {str(e)}")
        finally:
            # 임시 파일 정리
            if temp_session_file.exists():
                temp_session_file.unlink()
                st.write("🧹 임시 세션 파일 정리 완료")

if __name__ == "__main__":
    test_instagram_login() 