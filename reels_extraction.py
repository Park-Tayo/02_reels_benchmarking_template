import instaloader
from pathlib import Path
import pandas as pd
from datetime import datetime
import whisper
import requests
import tempfile
import os
import subprocess
import openai
from api_config import get_api_config
import time
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

# 절대 경로 설정
BASE_DIR = Path("D:/cursor_ai/02_reels_benchmarking_template")

# 전역 변수로 Whisper 모델 한 번만 로드
_whisper_model = whisper.load_model("small")

def get_whisper_model():
    global _whisper_model
    return _whisper_model

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
            
        model = get_whisper_model()
        result = model.transcribe(audio_path)
        
        os.remove(audio_path)
        return result["text"]
        
    except Exception as e:
        print(f"전사 오류: {e}")
        return ""

@timer_decorator
def translate_to_korean(text):
    """영어 텍스트를 한국어로 번역하되, 특수문자와 이모티콘은 유지합니다."""
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        prompt = f"""
        다음 텍스트를 한국어로 번역해주세요. 단, 다음 규칙을 반드시 지켜주세요:
        1. 전문 용어나 브랜드명 등 한국어로 번역이 어려운 영어 단어는 원문 그대로 유지
        2. 이모티콘과 특수문자(예: ✨, 🔥, #)는 그대로 유지
        3. 해시태그는 영어로 된 경우 원문 유지
        
        원문:
        {text}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 전문 번역가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"번역 중 오류 발생: {e}")
        return text

@timer_decorator
def process_transcript(transcript, caption, video_analysis):
    """번역과 정제를 하나의 GPT 호출로 통합"""
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        prompt = f"""
        다음은 영상에서 추출된 스크립트입니다. 다음 작업을 순서대로 수행해주세요:
        1. 영어로 된 경우 한국어로 번역 (단, 전문용어/브랜드명/해시태그는 원문 유지)
        2. 캡션과 영상 분석 내용을 참고하여 스크립트의 오탈자와 잘못 인식된 단어들을 수정
        3. 전체적으로 자연스러운 한국어로 정제
        
        원본 스크립트:
        {transcript}
        
        참고할 캡션:
        {caption}
        
        영상 분석 내용:
        - 초반 3초 (카피라이팅): {video_analysis.get('intro_copy', '')}
        - 초반 3초 (영상 구성): {video_analysis.get('intro_structure', '')}
        - 나레이션: {video_analysis.get('narration', '')}
        
        최종 정제된 스크립트만 반환해주세요.
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
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"스크립트 처리 중 오류 발생: {e}")
        return transcript

@timer_decorator
def extract_reels_info(url, video_analysis=None):
    L = instaloader.Instaloader()
    shortcode = url.split("/p/")[1].strip("/")
    
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        video_url = post.video_url
        
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
            
    except Exception as e:
        return f"에러 발생: {str(e)}"

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
    """Instagram 릴스 비디오를 다운로드합니다."""
    try:
        L = instaloader.Instaloader()
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
                    if done % 5 == 0:  # 진행률 업데이트 빈도 조절
                        print(f"\r💫 다운로드 진행률: [{'=' * done}{'.' * (50-done)}] {downloaded}/{total_size} bytes", end='')
        
        print("\n✅ 비디오 다운로드 완료!")
        return temp_video.name
        
    except instaloader.exceptions.InstaloaderException as e:
        print(f"⚠️ Instagram 관련 오류: {str(e)}")
        return None
    except Exception as e:
        print(f"⚠️ 예상치 못한 오류: {str(e)}")
        return None