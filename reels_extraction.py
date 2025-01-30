import instaloader
from pathlib import Path
import pandas as pd
from datetime import datetime
import whisper
import requests
import tempfile

# 절대 경로 설정
BASE_DIR = Path("D:/cursor_ai/02_reels_benchmarking_template")

def download_video(url):
    response = requests.get(url)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            tmp_file.write(response.content)
            return tmp_file.name
    return None

def transcribe_video(video_path):
    model = whisper.load_model("large")
    result = model.transcribe(video_path)
    return result["text"]

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
        video_path = download_video(video_url)
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
        
        # 정보 추출 (새로운 순서로)
        info = {
            'shortcode': shortcode,
            'date': post.date.strftime('%Y-%m-%d %H:%M:%S'),
            'transcript': transcript,
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
