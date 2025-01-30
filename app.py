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

# .env 파일 로드
load_dotenv()

# API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_api_config():
    if not OPENAI_API_KEY:
        raise ValueError("API 설정이 없습니다. .env 파일을 확인해주세요.")
    
    return {
        "api_key": OPENAI_API_KEY
    }

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

@st.cache_data(ttl=3600)
def analyze_with_gpt4(info, input_data):
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        # API 요청 데이터 구성
        messages = [
            {
                "role": "system",
                "content": "릴스 분석을 수행하는 전문가입니다."
            },
            {
                "role": "user",
                "content": f"""
                다음 릴스를 분석해주세요:
                
                스크립트: {info['transcript']}
                캡션: {info['caption']}
                사용자 입력: {input_data}
                """
            }
        ]
        
        # API 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=1000
        )
        
        # 응답 처리
        analysis_result = response.choices[0].message.content
        
        # 여기서 응답을 우리가 원하는 형식으로 변환
        return format_analysis_result(analysis_result)
        
    except Exception as e:
        return {"error": f"분석 중 오류 발생: {str(e)}"}

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
    
    # 3. 벤치마킹 분석
    st.subheader("3. 벤치마킹 분석")
    
    # 주제 분석
    with st.expander("주제 분석", expanded=True):
        for category, details in results["topic_analysis"].items():
            if details["checked"]:
                st.markdown(f"✅ **{category}**")
                st.markdown("관련 내용:")
                for evidence in details["evidence"]:
                    source_type = evidence["source"]  # "transcript" 또는 "caption"
                    content = evidence["content"]
                    st.markdown(f"- {source_type}: `{content}`")
            else:
                st.markdown(f"❌ **{category}**")
    
    # 초반 3초 분석
    with st.expander("초반 3초 분석", expanded=True):
        # 카피라이팅
        st.markdown("**카피라이팅**")
        for category, details in results["intro_copy_analysis"].items():
            if details["checked"]:
                st.markdown(f"✅ **{category}**")
                st.markdown("관련 내용:")
                for evidence in details["evidence"]:
                    source_type = evidence["source"]
                    content = evidence["content"]
                    st.markdown(f"- {source_type}: `{content}`")
            else:
                st.markdown(f"❌ **{category}**")
        
        # 영상 구성
        st.markdown("**영상 구성**")
        for category, details in results["intro_structure_analysis"].items():
            if details["checked"]:
                st.markdown(f"✅ **{category}**")
                st.markdown("관련 내용:")
                for evidence in details["evidence"]:
                    source_type = evidence["source"]
                    content = evidence["content"]
                    st.markdown(f"- {source_type}: `{content}`")
            else:
                st.markdown(f"❌ **{category}**")
    
    # 내용 구성 분석
    with st.expander("내용 구성 분석", expanded=True):
        for category, details in results["content_analysis"].items():
            if details["checked"]:
                st.markdown(f"✅ **{category}**")
                st.markdown("관련 내용:")
                for evidence in details["evidence"]:
                    source_type = evidence["source"]
                    content = evidence["content"]
                    st.markdown(f"- {source_type}: `{content}`")
            else:
                st.markdown(f"❌ **{category}**")
    
    # 개선할 점
    st.subheader("4. 개선할 점")
    for point in results["improvements"]:
        st.markdown(f"- {point}")
    
    # 적용할 점
    st.subheader("5. 적용할 점")
    for point in results["application_points"]:
        st.markdown(f"- {point}")

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