import instaloader
from pathlib import Path
import pandas as pd
from datetime import datetime
import requests
import tempfile
import os
import subprocess
import openai
from api_config import get_api_config
import time
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import streamlit as st  # Streamlit 설정 추가
from dotenv import load_dotenv

# 절대 경로 설정
BASE_DIR = Path("D:/cursor_ai/02_reels_benchmarking_template")

def get_whisper_model():
    # 위스퍼 모델 import 제거
    # import whisper 제거
    return None

def timer_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"[Timer] {func.__name__}: {end_time - start_time:.2f}초")
        return result
    return wrapper

@timer_decorator
def extract_audio_from_url(url):
    try:
        # FFmpeg 명령어로 URL에서 직접 오디오 추출
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        command = [
            'ffmpeg',
            '-i', url,  # URL에서 직접 스트리밍
            '-vn',  # 비디오 스트림 제거
            '-acodec', 'pcm_s16le',  # 오디오 코덱
            '-ar', '16000',  # 샘플링 레이트
            '-ac', '1',  # 모노 채널
            '-y',  # 기존 파일 덮어쓰기
            temp_audio
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return temp_audio
    except Exception as e:
        print(f"오디오 추출 실패: {e}")
        return None

@timer_decorator
def transcribe_video(video_url):
    try:
        audio_path = extract_audio_from_url(video_url)
        if not audio_path:
            return ""
            
        # OpenAI API를 사용한 음성 인식
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        with open(audio_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"  # 한국어 설정
            )
        
        os.remove(audio_path)
        return transcript.text
        
    except Exception as e:
        print(f"전사 오류: {e}")
        return ""

def check_and_refresh_credentials():
    """Instagram 인증 정보를 확인하고 갱신합니다."""
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    
    try:
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
        
        try:
            session_file = f"{INSTAGRAM_USERNAME}_instagram_session"
            
            try:
                L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                L.save_session_to_file(session_file)
                st.success("Instagram 로그인 성공")
                return True
                
            except instaloader.exceptions.ConnectionException as e:
                if "Checkpoint required" in str(e):
                    checkpoint_url = str(e).split("Point your browser to ")[1].split(" -")[0]
                    st.error("Instagram 보안 확인이 필요합니다!")
                    st.warning("""
                    다음 단계를 따라주세요:
                    1. Instagram에 웹브라우저로 로그인하세요
                    2. 아래 링크를 클릭하여 보안 확인을 완료하세요
                    3. 보안 확인 완료 후 다시 시도해주세요
                    """)
                    st.markdown(f"[보안 확인 링크]({checkpoint_url})")
                    
                    # 로그인 폼 표시
                    with st.form("login_form"):
                        st.write("보안 확인 완료 후 다시 로그인해주세요:")
                        username = st.text_input("Instagram 사용자명:", value=INSTAGRAM_USERNAME)
                        password = st.text_input("Instagram 비밀번호:", type="password")
                        submit = st.form_submit_button("다시 시도")
                        
                        if submit and username and password:
                            # .env 파일 업데이트
                            env_path = Path('.env')
                            if env_path.exists():
                                with open(env_path, 'r', encoding='utf-8') as f:
                                    lines = f.readlines()
                                
                                with open(env_path, 'w', encoding='utf-8') as f:
                                    for line in lines:
                                        if line.startswith('INSTAGRAM_USERNAME='):
                                            f.write(f'INSTAGRAM_USERNAME={username}\n')
                                        elif line.startswith('INSTAGRAM_PASSWORD='):
                                            f.write(f'INSTAGRAM_PASSWORD={password}\n')
                                        else:
                                            f.write(line)
                            
                            # 환경 변수 다시 로드
                            load_dotenv(override=True)
                            st.success("인증 정보가 업데이트되었습니다.")
                            st.experimental_rerun()
                    
                    return False
                else:
                    st.error(f"Instagram 연결 오류: {str(e)}")
                    return False
                    
        except Exception as e:
            st.error(f"Instagram 로그인 실패: {str(e)}")
            return False
            
    except Exception as e:
        st.error(f"인증 확인 중 오류 발생: {str(e)}")
        return False

@timer_decorator
def extract_reels_info(url, video_analysis=None):
    # 인증 정보 확인 및 갱신
    if not check_and_refresh_credentials():
        return None
        
    # Instaloader 인스턴스 생성 시 세션 파일 사용
    L = instaloader.Instaloader(
        max_connection_attempts=1,
        download_videos=False,
        download_geotags=False,
        download_comments=False,
        download_pictures=False,
        compress_json=False,
        save_metadata=False
    )
    
    try:
        shortcode = url.split("/p/")[1].strip("/")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        video_url = post.video_url
        
        if not video_url:
            st.error("이 게시물에서 비디오를 찾을 수 없습니다.")
            return None
            
        # 메타데이터 추출
        info = {
            'shortcode': shortcode,
            'date': post.date.strftime('%Y-%m-%d %H:%M:%S'),
            'caption': post.caption if post.caption else "",
            'view_count': post.video_view_count if hasattr(post, 'video_view_count') else 0,
            'video_duration': post.video_duration if hasattr(post, 'video_duration') else 0,
            'likes': post.likes,
            'comments': post.comments,
            'owner': post.owner_username,
            'video_url': video_url
        }
        
        # 트랜스크립션 수행
        transcript = transcribe_video(video_url)
        info['raw_transcript'] = transcript
        
        # 스크립트와 캡션 처리
        processed_result = process_transcript_and_caption(
            transcript=transcript,
            caption=info['caption'],
            video_analysis=video_analysis or {}
        )
        
        info['refined_transcript'] = processed_result['transcript']
        info['caption'] = processed_result['caption']
        
        return info
            
    except instaloader.exceptions.InstaloaderException as e:
        st.error(f"Instagram 데이터 추출 실패: {str(e)}")
        return None
    except Exception as e:
        st.error(f"예상치 못한 오류: {str(e)}")
        return None

@timer_decorator
def process_transcript_and_caption(transcript, caption, video_analysis):
    """스크립트와 캡션의 번역/정제를 하나의 GPT 호출로 통합"""
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        prompt = f"""
        다음은 영상의 스크립트와 캡션입니다. 각각에 대해 다음 작업을 수행해주세요:
        1. 영어로 된 경우 한국어로 번역 (단, 전문용어/브랜드명/해시태그는 원문 유지)
        2. 이모티콘과 특수문자는 그대로 유지
        3. 전체적으로 자연스러운 한국어로 정제
        
        원본 스크립트:
        {transcript}
        
        원본 캡션:
        {caption}
        
        영상 분석 내용:
        - 초반 3초 (카피라이팅): {video_analysis.get('intro_copy', '')}
        - 초반 3초 (영상 구성): {video_analysis.get('intro_structure', '')}
        - 나레이션: {video_analysis.get('narration', '')}
        
        다음 형식으로 결과를 반환해주세요:
        ---스크립트---
        [정제된 스크립트]
        ---캡션---
        [정제된 캡션]
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 전문 번역가이자 스크립트 교정 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        
        # 결과 파싱
        transcript_part = result.split("---캡션---")[0].replace("---스크립트---", "").strip()
        caption_part = result.split("---캡션---")[1].strip()
        
        return {
            "transcript": transcript_part,
            "caption": caption_part
        }
        
    except Exception as e:
        print(f"텍스트 처리 중 오류 발생: {e}")
        return {
            "transcript": transcript,
            "caption": caption
        }

@timer_decorator
def download_video(url):
    # 인증 정보 확인 및 갱신
    if not check_and_refresh_credentials():
        return None
        
    # Instaloader 인스턴스 생성 시 세션 파일 사용
    L = instaloader.Instaloader(
        max_connection_attempts=1,
        download_videos=False,
        download_geotags=False,
        download_comments=False,
        download_pictures=False,
        compress_json=False,
        save_metadata=False
    )
    
    try:
        shortcode = url.split("/p/")[1].strip("/")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        if not post.is_video:
            print("⚠️ 이 게시물은 비디오가 아닙니다.")
            return None
            
        video_url = post.video_url
        if not video_url:
            print("⚠️ 비디오 URL을 가져올 수 없습니다.")
            return None
            
        # 임시 파일 생성
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        
        # 비디오 다운로드
        print("📥 비디오 다운로드 중...")
        response = requests.get(video_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(temp_video.name, 'wb') as video_file:
            if total_size == 0:
                video_file.write(response.content)
            else:
                downloaded = 0
                for data in response.iter_content(chunk_size=4096):
                    downloaded += len(data)
                    video_file.write(data)
                    done = int(50 * downloaded / total_size)
                    if done % 5 == 0:
                        print(f"\r💫 다운로드 진행률: [{'=' * done}{'.' * (50-done)}] {downloaded}/{total_size} bytes", end='')
        
        print("\n✅ 비디오 다운로드 완료!")
        return temp_video.name
        
    except instaloader.exceptions.InstaloaderException as e:
        print(f"⚠️ Instagram 관련 오류: {str(e)}")
        # 세션 파일이 있다면 삭제하고 재시도
        if os.path.exists(session_file):
            os.remove(session_file)
            print("⚠️ 세션이 만료되어 재로그인이 필요합니다. 다시 시도해주세요.")
        return None
    except Exception as e:
        print(f"⚠️ 예상치 못한 오류: {str(e)}")
        return None