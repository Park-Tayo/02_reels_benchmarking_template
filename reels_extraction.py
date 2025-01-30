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

# 절대 경로 설정
BASE_DIR = Path("D:/cursor_ai/02_reels_benchmarking_template")

def extract_audio(video_path, output_path):
    try:
        # FFmpeg 명령어로 오디오 추출
        command = [
            'ffmpeg',
            '-i', video_path,  # 입력 비디오
            '-vn',  # 비디오 스트림 제거
            '-acodec', 'pcm_s16le',  # 오디오 코덱
            '-ar', '16000',  # 샘플링 레이트
            '-ac', '1',  # 모노 채널
            '-y',  # 기존 파일 덮어쓰기
            output_path
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except Exception as e:
        print(f"오디오 추출 실패: {e}")
        return None

def download_video(url):
    response = requests.get(url)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            tmp_file.write(response.content)
            return tmp_file.name
    return None

def transcribe_video(video_path):
    try:
        # 임시 오디오 파일 경로 설정
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        # 비디오에서 오디오 추출
        audio_path = extract_audio(video_path, temp_audio)
        if not audio_path:
            return ""
            
        # Whisper 모델로 음성 인식
        model = whisper.load_model("small")
        result = model.transcribe(audio_path)
        
        # 임시 파일 삭제
        os.remove(audio_path)
        
        return result["text"]
        
    except Exception as e:
        print(f"전사 오류: {e}")
        return ""

def refine_transcript(transcript, caption, video_analysis):
    """
    GPT를 사용하여 추출된 스크립트를 정제합니다.
    """
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        prompt = f"""
        다음은 영상에서 추출된 스크립트입니다. 캡션과 영상 분석 내용을 참고하여 스크립트의 오탈자와 잘못 인식된 단어들을 수정해주세요.
        
        원본 스크립트:
        {transcript}
        
        참고할 캡션:
        {caption}
        
        영상 분석 내용:
        - 초반 3초 (카피라이팅): {video_analysis.get('intro_copy', '')}
        - 초반 3초 (영상 구성): {video_analysis.get('intro_structure', '')}
        - 나레이션: {video_analysis.get('narration', '')}
        
        위 내용을 참고하여 스크립트를 자연스럽게 수정해주세요. 수정된 스크립트만 반환해주세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 전문 영상 스크립트 교정 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"스크립트 정제 중 오류 발생: {e}")
        return transcript

def extract_reels_info(url):
    # Instaloader 인스턴스 생성
    L = instaloader.Instaloader()
    
    # URL에서 숏코드 추출
    shortcode = url.split("/p/")[1].strip("/")
    
    try:
        # 게시물 정보 가져오기
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # 결과 저장할 디렉토리 생성
        output_dir = BASE_DIR / "reels_output"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # 비디오 URL과 스크립트 추출
        video_url = post.video_url
        video_path = download_video(video_url)  # 비디오 다운로드
        
        # 스크립트 추출 (다운로드된 비디오 파일 사용)
        transcript = transcribe_video(video_path) if video_path else ""
        
        # 임시 파일 삭제
        if video_path:
            Path(video_path).unlink()
        
        # 음악 정보 추출 시도
        try:
            music_info = post.media_info.get('music_info', {})
            music_title = music_info.get('title', '')
            music_artist = music_info.get('artist', '')
        except:
            music_title = ''
            music_artist = ''
        
        # 정보 추출
        info = {
            'shortcode': shortcode,
            'date': post.date.strftime('%Y-%m-%d %H:%M:%S'),
            'transcript': transcript,  # 원본 스크립트 저장
            'raw_transcript': transcript,  # 원본 스크립트 별도 보관
            'caption': post.caption if post.caption else "",
            'view_count': post.video_view_count if hasattr(post, 'video_view_count') else 0,
            'video_duration': post.video_duration if hasattr(post, 'video_duration') else 0,
            'likes': post.likes,
            'comments': post.comments,
            'music_title': music_title,
            'music_artist': music_artist,
            'owner': post.owner_username,
            'video_url': video_url
        }
        
        return info
        
    except Exception as e:
        return f"에러 발생: {str(e)}"

if __name__ == "__main__":
    # CSV 파일명 설정 (현재 시간 포함)
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = BASE_DIR / f"reels_info_{current_time}.csv"
    
    # 사용 예시
    reels_url = "https://www.instagram.com/p/C_5jgbugE2_/"
    result = extract_reels_info(reels_url)
    
    if isinstance(result, dict):
        # DataFrame 생성 및 CSV 저장
        df = pd.DataFrame([result])
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"정보가 {csv_filename}에 저장되었습니다.")
    else:
        print(result)
