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
    
    # URL을 세션 상태로 관리
    if 'url' not in st.session_state:
        st.session_state.url = ''
    
    # 1. 벤치마킹 섹션
    st.header("1. 벤치마킹 정보 입력")
    url = st.text_input("릴스 URL 입력 후 엔터를 누르세요", value=st.session_state.url)
    
    # URL이 변경되면 세션 상태 업데이트
    if url != st.session_state.url:
        st.session_state.url = url
    
    # URL 입력 버튼 추가
    url_submit = st.button("URL 입력")
    
    # 폼 데이터를 세션 상태로 관리
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'video_intro_copy': '',
            'video_intro_structure': '',
            'narration': '',
            'music': '',
            'font': ''
        }
    
    # URL이 입력되었거나 URL 입력 버튼이 클릭되었을 때 처리
    if url and (url_submit or True):
        video_url = get_video_url(url)
        if video_url:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                try:
                    st.video(video_url)
                except:
                    st.error("동영상을 불러올 수 없습니다.")
            
            with col2:
                # 폼 추가
                with st.form(key='video_analysis_form'):
                    with st.expander("영상 분석", expanded=True):
                        st.session_state.form_data['video_intro_copy'] = st.text_area(
                            "초반 3초 (카피라이팅) 설명",
                            value=st.session_state.form_data['video_intro_copy'],
                            height=68,
                            help="다음 요소들을 고려하여 설명해주세요:\n"
                                 "1. 구체적 수치 ('월 500만원', '3일 만에' 등)\n"
                                 "2. 뇌 충격 ('망하는 과정', '실패한 이유' 등)\n"
                                 "3. 이익/손해 강조 ('놓치면 후회', '꼭 알아야 할' 등)\n"
                                 "4. 권위 강조 ('현직 대기업 임원', '10년 경력' 등)\n"
                                 "5. 예시: '현직 인사팀장이 알려주는 연봉 3천 협상법'"
                        )
                        
                        st.session_state.form_data['video_intro_structure'] = st.text_area(
                            "초반 3초 (영상 구성) 설명",
                            value=st.session_state.form_data['video_intro_structure'],
                            height=68,
                            help="다음 요소들을 고려하여 설명해주세요.:\n"
                                 "1. 상식 파괴 (예상 밖의 장면)\n"
                                 "2. 결과 먼저 보여주기 (Before & After)\n"
                                 "3. 부정적 상황 강조\n"
                                 "4. 공감 유도 (일상적 고민/불편함)\n"
                                 "5. 예시: '출근 시간에 편하게 누워서 일하는 직원들 모습'"
                        )
                        
                        st.session_state.form_data['narration'] = st.text_input(
                            "나레이션 설명",
                            value=st.session_state.form_data['narration'],
                            help="나레이션의 특징과 음질을 설명해주세요:\n"
                                 "1. 목소리 특징 (성별, 연령대, 톤)\n"
                                 "2. 말하기 스타일 (전문적/친근한)\n"
                                 "3. 음질 상태 (노이즈 없는 깨끗한 음질)\n"
                                 "4. 예시: '20대 여성의 친근한 톤, 깨끗한 마이크 음질'"
                        )
                        
                        st.session_state.form_data['music'] = st.text_input(
                            "음악 설명",
                            value=st.session_state.form_data['music'],
                            help="배경음악의 특징을 설명해주세요:\n"
                                 "1. 트렌디한 정도 (최신 유행 BGM)\n"
                                 "2. 영상과의 조화 (리듬감, 분위기)\n"
                                 "3. 장르 및 템포\n"
                                 "4. 예시: '트렌디한 K-pop, 영상의 템포와 잘 맞는 리듬'"
                        )
                        
                        st.session_state.form_data['font'] = st.text_input(
                            "폰트 설명",
                            value=st.session_state.form_data['font'],
                            help="화면에 보여지는 텍스트의 시각적 특징을 설명해주세요:\n"
                                 "1. 폰트 종류 (고딕체, 손글씨체 등)\n"
                                 "2. 강조 요소 (굵기, 크기, 테두리)\n"
                                 "3. 가독성 정도\n"
                                 "4. 예시: '눈에 띄는 굵은 글씨, 흰색 테두리, 노란색 배경'"
                        )
                    # 폼 제출 버튼
                    form_submit = st.form_submit_button("저장 (필수)")
            
            # URL이 입력되고 동영상이 성공적으로 로드된 경우에만 나머지 섹션 표시
            st.header("2. 내 콘텐츠 정보 입력")
            topic = st.text_area("제작할 콘텐츠에 대해 자유롭게 입력해주세요", height=68)
            
            # 분석 시작 버튼
            if st.button("분석 시작"):
                if not url:
                    st.warning("URL을 입력해주세요.")
                    return None
                
                with st.spinner("분석 중... (약 1분 30초 소요)"):
                    # 캐시된 결과 확인
                    results = get_cached_analysis(url, {
                        "url": url,
                        "video_analysis": {
                            "intro_copy": st.session_state.form_data['video_intro_copy'],
                            "intro_structure": st.session_state.form_data['video_intro_structure'],
                            "narration": st.session_state.form_data['narration'],
                            "music": st.session_state.form_data['music'],
                            "font": st.session_state.form_data['font']
                        },
                        "content_info": {
                            "topic": topic
                        }
                    })
                    
                    if results:
                        display_analysis_results(results["analysis"], results["reels_info"])
                    
                    return None
        else:
            st.error("Instagram URL에서 동영상을 찾을 수 없습니다.")
    
    return {
        "url": url,
        "video_analysis": {
            "intro_copy": st.session_state.form_data['video_intro_copy'],
            "intro_structure": st.session_state.form_data['video_intro_structure'],
            "narration": st.session_state.form_data['narration'],
            "music": st.session_state.form_data['music'],
            "font": st.session_state.form_data['font']
        },
        "content_info": {
            "topic": topic if 'topic' in locals() else ""
        }
    }

@st.cache_data(ttl=3600)
def analyze_with_gpt4(info, input_data):
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        messages = [
            {
                "role": "system",
                "content": """
                당신은 릴스 분석 전문가입니다. 다음 형식으로 분석 결과를 제공해주세요. 
                각 항목에 대해 ✅/❌를 표시하고, 그 판단의 근거가 되는 스크립트나 캡션의 구체적인 내용을 인용해주세요. 
                여기서 모수란 이 내용이 얼마나 많은 사람들의 관심을 끌 수 있는지에 대한 것입니다.
                문제 해결이란 시청자가 갖고 있는 문제를 해결해줄 수 있는지에 대한 것입니다:

                # 1. 주제: 
                - **(이 영상의 주제에 대한 내용)**
                - ✅/❌ **공유 및 저장**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **모수**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **욕망충족**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **흥미유발**: 스크립트/캡션 중 해당 내용

                # 2. 초반 3초
                ## 카피라이팅 :
                - **(이 영상의 초반 3초 카피라이팅에 대한 내용)**
                - ✅/❌ **구체적 수치**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **뇌 충격**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **이익, 손해 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **권위 강조**: 스크립트/캡션 중 해당 내용

                ## 영상 구성 : 
                - **(이 영상의 초반 3초 영상 구성에 대한 내용)**
                - ✅/❌ **상식 파괴**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **결과 먼저**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **부정 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **공감 유도**: 스크립트/캡션 중 해당 내용

                # 3. 내용 구성: 
                - **(이 영상의 스크립트/캡션의 전체적인 내용 구성에 대한 내용)**
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **호기심 유발**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **행동 유도**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **스토리**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **제안**: 스크립트/캡션 중 해당 내용

                # 4. 개선할 점:
                - ❌**(항목명)**: 개선할 점 설명 추가 ex. 스크립트/캡션 예시
                
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
                원본 영상의 구성을 최대한 유사하게 벤치마킹하되, 다음 요소들을 추가/보완했습니다:

                1. **도입부** (3초):
                   - 뇌 충격을 주는 구체적 수치 활용 (예시 내용)
                   - 상식을 깨는 내용으로 시작 (예시 내용)
                   - 결과를 먼저 보여주는 방식 적용 (예시 내용)
                   
                2. **전개**:
                   - 문제 해결형 구조 적용:
                     * 명확한 문제 제시 (예시 내용)
                     * 구체적인 해결책 제시 (예시 내용)
                   - 시청 지속성 확보:
                     * 나레이션과 영상의 일치성 유지 (예시 내용)
                     * 트렌디한 BGM 활용 (예시 내용)
                     * 고화질 영상 품질 유지 (예시 내용)
                   
                3. **마무리**:
                   - 행동 유도 요소 포함:
                     * 저장/공유 유도 멘트 (예시 내용)
                     * 팔로우 제안 (예시 내용)
                   - 캡션 최적화:
                     * 첫 줄 후킹 (예시 내용)
                     * 단락 구분으로 가독성 확보 (예시 내용)
                     * 구체적 수치/권위 요소 포함 (예시 내용)
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
    
    # 1. 릴스 정보
    st.subheader("1. 릴스 정보")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**기본 정보**")
        st.write(f"• 업로드 날짜: {reels_info['date']}")
        st.markdown(f"• 계정: <a href='https://www.instagram.com/{reels_info['owner']}' target='_blank'>@{reels_info['owner']}</a>", unsafe_allow_html=True)
        st.write(f"• 영상 길이: {reels_info['video_duration']:.1f}초")
    
    with col2:
        st.markdown("**시청 반응**")
        st.write(f"• 조회수: {format(reels_info['view_count'], ',')}회")
        st.write(f"• 좋아요: {format(reels_info['likes'], ',')}개")
        st.write(f"• 댓글: {format(reels_info['comments'], ',')}개")
    
    with col3:
        st.markdown("**음악 정보**")
        st.write(f"• 제목: {reels_info['music_title'] if reels_info.get('music_title') else '없음'}")
        st.write(f"• 아티스트: {reels_info['music_artist'] if reels_info.get('music_artist') else '없음'}")
    
    # 2. 스크립트와 캡션
    st.subheader("2. 콘텐츠 내용")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**스크립트**")
        st.write(reels_info["refined_transcript"])
    with col2:
        st.markdown("**캡션**")
        st.write(reels_info["caption"])
    
    # 3. GPT 분석 결과
    st.subheader("3. 벤치마킹 템플릿 분석")
    st.markdown(results)

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_analysis(url, input_data):
    try:
        # 스피너 제거 (상위 레벨의 스피너만 사용)
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

def get_reels_structure():
    return {
        "1. 도입부 (3초)": {
            "핵심요소": [
                "구체적 수치 활용",
                "상식을 깨는 내용",
                "결과 먼저 보여주기",
                "이익/손해 강조",
                "권위 요소 활용"
            ],
            "목적": "시청자의 즉각적인 관심 유도"
        },
        
        "2. 전개부": {
            "주요_구조": [
                "문제 해결형",
                "호기심 유발형", 
                "스토리텔링형"
            ],
            "필수_요소": [
                "고품질 영상/음향",
                "트렌디한 BGM",
                "명확한 메시지 전달"
            ]
        },
        
        "3. 마무리": {
            "행동유도": [
                "저장 유도",
                "공유 유도",
                "팔로우 제안"
            ],
            "캡션최적화": [
                "첫 줄 후킹",
                "단락 구분",
                "쉬운 표현 사용",
                "구체적 수치/권위 포함"
            ]
        }
    }

def main():
    input_data = create_input_form()

if __name__ == "__main__":
    main() 