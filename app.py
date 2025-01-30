import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from reels_extraction import download_video, extract_reels_info

# 페이지 기본 설정
st.set_page_config(
    page_title="릴스 벤치마킹 분석",
    page_icon="🎥",
    layout="wide"
)

# 스타일 설정
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 1rem;
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
    # GPT-4 분석 로직 구현
    # 실제 구현 시에는 OpenAI API 호출 필요
    try:
        analysis_result = {
            "topic": info["caption"],
            "topic_analysis": {
                "sharing": True,
                "audience": "광범위",
                "problem_solving": True,
                "desire": True,
                "interest": True
            },
            "video_analysis": {
                "intro_copy": {
                    "specific_numbers": True,
                    "brain_impact": True,
                    "benefit_emphasis": True,
                    "authority": False
                },
                "intro_structure": {
                    "common_sense_break": True,
                    "results_first": True,
                    "negative_emphasis": False,
                    "empathy": True
                }
            },
            "improvements": [
                "구체적인 예시 추가 필요",
                "권위 강조 요소 추가 필요"
            ],
            "application_points": [
                "간결한 제목 사용",
                "단계별 설명 제공",
                "공유 유도 문구 사용"
            ]
        }
        return analysis_result
    except Exception as e:
        return {"error": str(e)}

def display_analysis_results(results):
    st.header("2. 출력 양식")
    
    # 1. 벤치마킹 분석
    st.subheader("1) 벤치마킹 분석")
    
    # 주제
    st.write("주제:", results["topic"])
    
    # 주제 분석
    with st.expander("주제 분석"):
        cols = st.columns(5)
        analyses = ["공유 및 저장", "모수", "문제해결", "욕망충족", "흥미유발"]
        for col, analysis in zip(cols, analyses):
            with col:
                st.write(f"- {analysis}: ✓")
    
    # 영상 분석
    with st.expander("영상"):
        st.write("초반 3초 (카피라이팅)")
        for key, value in results["video_analysis"]["intro_copy"].items():
            st.write(f"- {key}: {'✓' if value else '✗'}")
            
        st.write("\n초반 3초 (영상 구성)")
        for key, value in results["video_analysis"]["intro_structure"].items():
            st.write(f"- {key}: {'✓' if value else '✗'}")
    
    # 개선할 점
    st.write("개선할 점:")
    for point in results["improvements"]:
        st.write(f"- {point}")
    
    # 적용할 점
    st.write("적용할 점:")
    for point in results["application_points"]:
        st.write(f"- {point}")

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
            info = extract_reels_info(url)
            if isinstance(info, str):
                st.error(f"정보 추출 실패: {info}")
                return None
            
            # 3. GPT-4 분석
            analysis = analyze_with_gpt4(info, input_data)
            if "error" in analysis:
                st.error(f"AI 분석 실패: {analysis['error']}")
                return None
            
            return analysis
            
    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {str(e)}")
        return None

def main():
    input_data = create_input_form()
    
    if st.button("분석 시작"):
        if not input_data["url"]:
            st.warning("URL을 입력해주세요.")
            return
            
        # 캐시된 결과 확인
        results = get_cached_analysis(input_data["url"], input_data)
        
        if results:
            display_analysis_results(results)

if __name__ == "__main__":
    main() 