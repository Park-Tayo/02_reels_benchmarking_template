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

def create_input_form():
    st.title("릴스 벤치마킹 분석")
    
    # 1. 벤치마킹 섹션
    st.header("1. 벤치마킹")
    url = st.text_input("URL")
    
    with st.expander("영상 분석"):
        video_intro_copy = st.text_area("초반 3초 (카피라이팅) 설명")
        video_intro_structure = st.text_area("초반 3초 (영상 구성) 설명")
        narration = st.text_area("나레이션 설명")
        music = st.text_area("음악 설명")
        font = st.text_area("폰트 설명")
    
    # 2. 내 콘텐츠 정보
    st.header("2. 내 콘텐츠 정보")
    topic = st.text_input("주제 선정")
    
    return {
        "url": url,
        "video_analysis": {
            "intro_copy": video_intro_copy,
            "intro_structure": video_intro_structure,
            "narration": narration,
            "music": music,
            "font": font
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
                - 

                # 5. 적용할 점:
                - 
                """
            },
            {
                "role": "user",
                "content": f"""
                다음 릴스를 분석해주세요:
                
                스크립트: {info['transcript']}
                캡션: {info['caption']}
                
                사용자 입력 정보:
                - 초반 3초 카피라이팅: {input_data['video_analysis']['intro_copy']}
                - 초반 3초 영상 구성: {input_data['video_analysis']['intro_structure']}
                - 나레이션: {input_data['video_analysis']['narration']}
                - 음악: {input_data['video_analysis']['music']}
                - 폰트: {input_data['video_analysis']['font']}
                - 주제: {input_data['content_info']['topic']}
                """
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=2000
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
        st.write(reels_info["transcript"])
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
            
            # 2. 정보 추출
            reels_info = extract_reels_info(url)
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