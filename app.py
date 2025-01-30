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

# .env 파일 로드
load_dotenv()

# API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 페이지 기본 설정
st.set_page_config(
    page_title="릴스 벤치마킹 분석",
    page_icon="🎥",
    layout="centered"
)

# 스타일 설정
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    .stVideo {
        width: 100%;
        max-width: 400px !important;
        margin: 0 auto;
    }
    .video-container {
        display: flex;
        flex-direction: row;
        gap: 2rem;
        margin-bottom: 2rem;
    }
    .video-section {
        flex: 0 0 400px;
    }
    .content-section {
        flex: 1;
    }
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    @media (max-width: 768px) {
        .video-container {
            flex-direction: column;
        }
        .video-section {
            flex: none;
            width: 100%;
        }
    }
    </style>
""", unsafe_allow_html=True)

def get_video_url(url):
    try:
        # Instaloader 인스턴스 생성
        L = instaloader.Instaloader()
        
        # URL에서 숏코드 추출
        shortcode = url.split("/p/")[1].strip("/")
        
        # 게시물 정보 가져오기
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # 비디오 URL 반환
        return post.video_url if post.is_video else None
        
    except Exception as e:
        return None

def create_input_form():
    st.title("릴스 벤치마킹 분석")
    
    # 1. 벤치마킹 섹션
    st.header("1. 벤치마킹")
    url = st.text_input("URL 입력 후 엔터를 누르세요")
    
    if url:  # URL이 입력되었을 때만 표시
        video_url = get_video_url(url)
        if video_url:
            col1, col2 = st.columns([1, 1])  # 1:1 비율로 컬럼 분할
            
            with col1:
                try:
                    st.video(video_url)
                except:
                    st.error("동영상을 불러올 수 없습니다.")
            
            with col2:
                with st.expander("영상 분석", expanded=True):  # 자동으로 펼쳐진 상태
                    video_intro_copy = st.text_area("초반 3초 (카피라이팅) 설명", height=68)
                    video_intro_structure = st.text_area("초반 3초 (영상 구성) 설명", height=68)
                    narration = st.text_area("나레이션 설명", height=68)
                    music = st.text_area("음악 설명", height=68)
                    font = st.text_area("폰트 설명", height=68)
        else:
            st.error("Instagram URL에서 동영상을 찾을 수 없습니다.")
    
    # 2. 내 콘텐츠 정보
    st.header("2. 내 콘텐츠 정보")
    topic = st.text_input("주제 선정")
    
    return {
        "url": url,
        "video_analysis": {
            "intro_copy": video_intro_copy if 'video_intro_copy' in locals() else "",
            "intro_structure": video_intro_structure if 'video_intro_structure' in locals() else "",
            "narration": narration if 'narration' in locals() else "",
            "music": music if 'music' in locals() else "",
            "font": font if 'font' in locals() else ""
        },
        "content_info": {
            "topic": topic
        }
    }

def clean_json_response(response_text):
    """
    코드 블록을 제거하고 순수한 JSON 문자열만 반환합니다.
    """
    # 코드 블록 제거
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```', '', response_text)
    return response_text.strip()

@st.cache_data(ttl=3600)
def analyze_with_gpt4(info, input_data):
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        messages = [
            {
                "role": "system",
                "content": """
                당신은 릴스 분석 전문가입니다. 다음 형식으로 분석 결과를 제공해주세요. 각 항목에 대해 ✅/❌를 표시하고, 그 판단의 근거가 되는 스크립트나 캡션의 구체적인 내용을 인용해주세요:

                # 1. 주제:
                - ✅/❌ **공유 및 저장**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **모수**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **욕망충족**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **흥미유발**: 스크립트/캡션 중 해당 내용

                # 2. 초반 3초:
                ## 카피라이팅
                - ✅/❌ **구체적 수치**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **뇌 충격**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **이익, 손해 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **권위 강조**: 스크립트/캡션 중 해당 내용

                ## 영상 구성
                - ✅/❌ **상식 파괴**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **결과 먼저**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **부정 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **공감 유도**: 스크립트/캡션 중 해당 내용

                # 3. 내용 구성:
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **호기심 유발**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **행동 유도**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **스토리**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **제안**: 스크립트/캡션 중 해당 내용

                # 4. 개선할 점:
                -❌**(항목명)**: 개선할 점 설명 추가 ex. 스크립트/캡션 예시

                # 5. 적용할 점:
                - ✅**(항목명)**: 적용할 점 설명 추가 ex. 스크립트/캡션 중 해당 내용

                # 6. 벤치마킹 적용 기획:
                {f'''
                입력하신 주제 "{input_data["content_info"]["topic"]}"에 대한 벤치마킹 적용 기획입니다.
                위에서 체크(✅)된 항목들을 모두 반영하여 벤치마킹한 내용입니다.
                
                [시스템 참고용 - 출력하지 말 것]
                - 스크립트: {info['refined_transcript']}
                - 캡션: {info['caption']}
                
                위 스크립트와 캡션을 최대한 유사하게 벤치마킹하여 다음과 같이 작성했습니다:
                
                ## 스크립트 예시:
                [원본 스크립트의 문장 구조, 호흡, 강조점을 거의 그대로 활용하되 새로운 주제에 맞게 변경.
                예를 들어 원본이 "이것 하나만 있으면 ~~" 구조라면, 새로운 주제도 동일한 구조 사용]

                ## 캡션 예시:
                [원본 캡션의 구조를 거의 그대로 활용.
                예를 들어 원본이 "✨꿀팁 공개✨" 시작이라면, 새로운 캡션도 동일한 구조 사용.
                이모지, 해시태그 스타일도 원본과 동일하게 구성]

                ## 영상 기획:
                원본 영상의 구성을 최대한 유사하게 벤치마킹했습니다.
                1. **도입부** (3초):
                   [원본의 도입부 구성을 그대로 차용]
                2. **전개**:
                   [원본의 전개 방식을 그대로 차용]
                3. **마무리**:
                   [원본의 마무리 방식을 그대로 차용]
                
                ※ 위 기획은 체크된 항목들({체크된 항목들 나열})을 모두 반영했습니다.
                ''' if input_data["content_info"]["topic"] else "주제가 입력되지 않았습니다. 구체적인 기획을 위해 주제를 입력해주세요."}
                """
            },
            {
                "role": "user",
                "content": f"""
                다음 릴스를 분석하고, 입력된 주제에 맞게 벤치마킹 기획을 해주세요:
                
                스크립트: {info['refined_transcript']}
                캡션: {info['caption']}
                
                사용자 입력 정보:
                - 초반 3초 카피라이팅: {input_data['video_analysis']['intro_copy']}
                - 초반 3초 영상 구성: {input_data['video_analysis']['intro_structure']}
                - 나레이션: {input_data['video_analysis']['narration']}
                - 음악: {input_data['video_analysis']['music']}
                - 폰트: {input_data['video_analysis']['font']}
                
                벤치마킹할 새로운 주제: {input_data['content_info']['topic']}
                
                위 릴스의 장점과 특징을 분석한 후, 새로운 주제에 맞게 벤치마킹하여 구체적인 스크립트, 캡션, 영상 기획을 제시해주세요.
                """
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=10000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
        return f"분석 중 오류 발생: {str(e)}"

def display_analysis_results(results, reels_info):
    st.header("분석 결과")
    
    # 1. 동영상 미리보기
    st.subheader("1. 릴스 영상")
    st.video(reels_info["video_url"])
    
    # 2. 스크립트와 캡션
    st.subheader("2. 콘텐츠 내용")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**스크립트**")
        st.write(reels_info["refined_transcript"])  # 무조건 정제된 스크립트 표시
    with col2:
        st.markdown("**캡션**")
        st.write(reels_info["caption"])
    
    # 3. GPT 분석 결과
    st.subheader("3. 벤치마킹 템플릿 분석")
    st.markdown(results)

@st.cache_data(ttl=3600)
def get_cached_analysis(url, input_data):
    try:
        with st.spinner('영상 분석 중... (최대 2분 소요)'):
            # 1. 영상 다운로드
            video_path = download_video(url)
            if not video_path:
                st.error("영상 다운로드에 실패했습니다. URL을 확인해주세요.")
                return None
            
            # 2. 정보 추출 (video_analysis 전달)
            reels_info = extract_reels_info(url, input_data['video_analysis'])
            if isinstance(reels_info, str):
                st.error(f"정보 추출 실패: {reels_info}")
                return None
            
            # 3. GPT-4 분석
            analysis = analyze_with_gpt4(reels_info, input_data)
            if "error" in analysis:
                st.error(f"AI 분석 실패: {analysis['error']}")
                return None
            
            return {
                "analysis": analysis,
                "reels_info": reels_info
            }
            
    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {str(e)}")
        return None

def format_analysis_result(analysis_text):
    """GPT-4 응답을 구조화된 형식으로 변환합니다."""
    return {
        "topic_analysis": {
            "주제 명확성": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            },
            "타겟 적합성": {
                "checked": True,
                "evidence": [{"source": "caption", "content": "예시 내용"}]
            }
        },
        "intro_copy_analysis": {
            "호기심 유발": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            },
            "핵심 가치 전달": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            }
        },
        "intro_structure_analysis": {
            "시각적 임팩트": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            },
            "브랜딩 요소": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            }
        },
        "content_analysis": {
            "스토리텔링": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            },
            "정보 전달력": {
                "checked": True,
                "evidence": [{"source": "transcript", "content": "예시 내용"}]
            }
        },
        "improvements": [
            "개선점 1",
            "개선점 2"
        ],
        "application_points": [
            "적용할 점 1",
            "적용할 점 2"
        ]
    }

def main():
    input_data = create_input_form()
    
    if st.button("분석 시작"):
        if not input_data["url"]:
            st.warning("URL을 입력해주세요.")
            return
            
        # 캐시된 결과 확인
        results = get_cached_analysis(input_data["url"], input_data)
        
        if results:
            display_analysis_results(results["analysis"], results["reels_info"])

if __name__ == "__main__":
    main() 