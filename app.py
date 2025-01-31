import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from reels_extraction import download_video, extract_reels_info
import os
from dotenv import load_dotenv
from api_config import get_api_config
import requests
import openai
import re
import instaloader
import time
from urllib.parse import urlparse

# 페이지 설정을 가장 먼저 호출
st.set_page_config(
    page_title="✨ 릴스 벤치마킹 스튜디오",
    page_icon="🎥",
    layout="centered"
)

# .env 파일 로드
load_dotenv()

def validate_env_vars():
    required_vars = ["INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        st.error(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        return False
    return True

def test_instagram_login():
    st.title("✨ 릴스 벤치마킹 스튜디오")
    st.markdown("### 🔒 Instagram 로그인 테스트")
    
    # 환경 변수 확인
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    
    # 환경 변수 상태 표시
    st.write("## 📋 환경 변수 상태")
    st.write(f"- USERNAME 설정됨: {'✅' if INSTAGRAM_USERNAME else '❌'}")
    st.write(f"- PASSWORD 설정됨: {'✅' if INSTAGRAM_PASSWORD else '❌'}")
    
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
                
                # 일반 로그인 시도
                L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                
                # 로그인 성공 확인
                test_profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
                st.success("✅ 로그인 성공!")
                
        except instaloader.exceptions.BadCredentialsException:
            st.error("❌ 로그인 실패: 잘못된 사용자 이름 또는 비밀번호")
        except instaloader.exceptions.ConnectionException as e:
            st.error(f"❌ 연결 오류: {str(e)}")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            st.error("❌ 2단계 인증이 필요합니다")
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류: {str(e)}")

def main():
    # 환경 변수 검증
    if not validate_env_vars():
        st.stop()
    
    # 로그인 테스트 실행
    test_instagram_login()

if __name__ == "__main__":
    main() 