import streamlit as st
import sqlite3
import pandas as pd
import os
import textwrap  # [추가] HTML 들여쓰기 문제 해결용 도구
from openai import OpenAI  # 👈 이 줄이 꼭 필요합니다!



# [추가할 부분] OpenAI 클라이언트 설정
# "sk-..." 부분에 본인의 실제 API 키를 넣으세요.
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# 페이지 설정
st.set_page_config(page_title="샤모아 - 서울대 해외 프로그램 알리미", page_icon="✈️", layout="wide")

# ==========================================
# [CSS] 디자인 (카드 및 UI 스타일)
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #f9fafb; }
    
    /* 카드 디자인 */
    .program-card {
        background-color: white;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        border: 1px solid #f0f0f0;
        transition: transform 0.2s;
        height: 380px; 
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
    }
    .program-card:hover { transform: translateY(-5px); }

    .card-content { flex: 1; }

    .flag-icon {
        font-size: 40px;
        position: absolute;
        top: 20px;
        right: 20px;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        background-color: #f2f4f6;
        color: #4e5968;
        margin-bottom: 10px;
    }
    
    .card-title {
        font-size: 20px;
        font-weight: 700;
        color: #191f28;
        margin-bottom: 8px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        padding-right: 50px;
    }
    
    .period-info {
        font-size: 14px;
        color: #3182f6; 
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .card-desc {
        font-size: 15px;
        color: #4e5968;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .action-btn {
        display: block;
        width: 100%;
        text-align: center;
        background-color: #e8f3ff;
        color: #1b64da;
        text-decoration: none;
        padding: 12px 0;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 600;
        transition: 0.2s;
        margin-top: 15px;
    }
    .action-btn:hover {
        background-color: #3182f6;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# [함수] 데이터 로드 및 유틸리티
# ==========================================
def load_data():
    conn = sqlite3.connect('snu_programs.db')
    df = pd.read_sql_query("SELECT * FROM programs", conn)
    conn.close()
    return df


def get_chatbot_context():
    """챗봇에게 주입할 프로그램 데이터(지식)를 텍스트로 만듭니다."""
    con = sqlite3.connect('snu_programs.db')
    df = pd.read_sql("SELECT * FROM programs WHERE status IN ('YES', 'CHECK')", con)
    con.close()
    
    if df.empty:
        return "현재 수집된 해외 프로그램 정보가 없습니다."
    
    context_text = "다음은 현재 모집 중이거나 확인이 필요한 서울대학교 해외 프로그램 목록입니다:\n\n"
    
    for idx, row in df.iterrows():
        context_text += f"[{idx+1}] 프로그램명: {row['title']}\n"
        context_text += f" - 상태: {row['status']}\n"
        context_text += f" - 출처: {row['site_name']}\n"
        context_text += f" - 대상: {row['target']}\n"
        context_text += f" - 기간: {row['period']}\n"
        context_text += f" - 내용요약: {row['reason']}\n"
        context_text += f" - 링크: {row['link']}\n\n"
        
    return context_text


def get_flag_icon(text):
    if not text: return "🌏"
    text = text.lower()
    
    # 1. 북미/남미
    if any(x in text for x in ['미국', 'usa', 'america', 'new york', 'boston', 'washington', 'california']): return "🇺🇸"
    if any(x in text for x in ['캐나다', 'canada']): return "🇨🇦"
    
    # 2. 아시아
    if any(x in text for x in ['일본', 'japan', 'tokyo', 'osaka']): return "🇯🇵"
    if any(x in text for x in ['중국', 'china', 'beijing']): return "🇨🇳"
    if any(x in text for x in ['대만', 'taiwan']): return "🇹🇼"
    if any(x in text for x in ['베트남', 'vietnam']): return "🇻🇳"
    if any(x in text for x in ['태국', 'thailand']): return "🇹🇭"
    if any(x in text for x in ['싱가포르', 'singapore']): return "🇸🇬"
    if any(x in text for x in ['인도네시아', 'indonesia']): return "🇮🇩"
    if any(x in text for x in ['인도', 'india']): return "🇮🇳"
    if any(x in text for x in ['필리핀', 'philippines']): return "🇵🇭"
    
    # 3. 유럽
    if any(x in text for x in ['영국', 'uk', 'london']): return "🇬🇧"
    if any(x in text for x in ['프랑스', 'france', 'paris']): return "🇫🇷"
    if any(x in text for x in ['독일', 'germany', 'berlin']): return "🇩🇪"
    if any(x in text for x in ['이탈리아', 'italy']): return "🇮🇹"
    if any(x in text for x in ['스페인', 'spain']): return "🇪🇸"
    if any(x in text for x in ['스위스', 'swiss']): return "🇨🇭"
    
    # 4. 오세아니아
    if any(x in text for x in ['호주', 'australia']): return "🇦🇺"
    if any(x in text for x in ['뉴질랜드', 'new zealand']): return "🇳🇿"
    
    return "🌏"

# ==========================================
# [헤더] 상단 로고 및 제목
# ==========================================
col1, col2 = st.columns([0.8, 9]) 

with col1:
    st.write("") 
    if os.path.exists("snu_logo.png"):
        st.image("snu_logo.png", width=80)
    else:
        st.image("https://upload.wikimedia.org/wikipedia/ko/thumb/d/db/Seoul_National_University_Emblem.png/800px-Seoul_National_University_Emblem.png", width=80)

with col2:
    st.markdown("""
    <div style="display: flex; flex-direction: column; justify-content: center; height: 100px;">
        <h1 style='margin: 0; font-size: 32px; color: #191f28;'>샤모아 - 서울대 해외 프로그램 알리미</h1>
        <p style='margin: 8px 0 0 0; color: #8b95a1; font-size: 16px;'>
            흩어진 해외 프로그램 공지, AI가 한곳에 모았습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

# ==========================================
# [메인] 탭 구성
# ==========================================
try:
    df = load_data()
except:
    st.error("데이터베이스를 찾을 수 없습니다. crawling.py를 먼저 실행해주세요.")
    st.stop()

tab0, tab1, tab2, tab3 = st.tabs(["🏠사이트 소개", "🚀 추천 프로그램", "🔍 더 찾아보기", "🤖 AI 상담"])


# ----------------------------------------------------------------
# [Tab 0] 홈 (샤모아 소개)
# ----------------------------------------------------------------
with tab0:
    # Toss 스타일 CSS (폰트 크기, 여백 최적화)
    st.markdown("""
    <style>
        .hero-container {
            text-align: center;
            padding: 100px 20px; /* 위아래 여백을 넉넉하게 줘서 시원한 느낌 */
            background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%); /* 살짝 그라데이션 */
            border-radius: 24px;
            margin-bottom: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03); /* 아주 연한 그림자 */
        }
        .brand-label {
            font-size: 1.2rem;
            font-weight: 700;
            color: #3182F6; /* Toss 블루 */
            margin-bottom: 16px;
            letter-spacing: -0.5px;
        }
        .main-title {
            font-size: 3.2rem;
            font-weight: 800;
            color: #191F28;
            line-height: 1.4;
            margin-bottom: 24px;
            word-break: keep-all;
        }
        .sub-title {
            font-size: 1.35rem;
            color: #4E5968;
            font-weight: 500;
            line-height: 1.7;
            margin-bottom: 40px;
            word-break: keep-all;
        }
        .feature-card {
            background-color: white;
            padding: 32px;
            border-radius: 20px;
            text-align: center;
            height: 100%;
            border: 1px solid #f0f0f0;
            transition: transform 0.2s;
        }
        .feature-card:hover { transform: translateY(-5px); }
        .feature-icon { font-size: 48px; margin-bottom: 16px; }
        .feature-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 12px; color: #333; }
        .feature-desc { font-size: 1rem; color: #6b7684; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

    # --- [1] 메인 히어로 섹션 (수정된 문구 적용) ---
    st.markdown("""
    <div class="hero-container">
        <div class="brand-label">서울대 해외 프로그램 모아보기, 샤모아</div>
        <div class="main-title">
            나만 몰랐던 해외 프로그램,<br>
            이제 놓치지 말고 챙겨가세요 🚀
        </div>
        <div class="sub-title">
            홈페이지마다 들어가서 찾느라 기회를 놓친 적 있다면 이제 안심하세요.<br>
            복잡한 검색 없이, 나에게 딱 맞는 해외 파견 공지만 모아서 보여드려요.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- [2] 기능 소개 (카드 3개) ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">👀</div>
            <div class="feature-title">한눈에 모아보기</div>
            <div class="feature-desc">
                단과대별로 흩어진 공지사항,<br>
                이제 '샤모아'에서 한 번에 확인하세요.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">✨</div>
            <div class="feature-title">AI 핵심 요약</div>
            <div class="feature-desc">
                복잡한 모집 요강을 다 읽을 필요 없어요.<br>
                AI가 핵심 내용과 혜택만 요약해줍니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">맞춤형 상담</div>
            <div class="feature-desc">
                "이번 겨울에 갈 수 있는 곳은?"<br>
                궁금한 건 AI 챗봇에게 바로 물어보세요.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("") # 여백 추가
    st.divider() # 하단 구분선



import re
from difflib import SequenceMatcher

# ----------------------------------------------------------------
# [Tab 1] YES인 프로그램 (강력한 중복 제거 적용)
# ----------------------------------------------------------------
with tab1:
    yes_programs = df[df['status'] == 'YES']
    
    import re
    from difflib import SequenceMatcher

    # --- [초강력 중복 제거 알고리즘 V2] ---
    unique_programs = []

    # 1. 텍스트 정제 함수 (특수문자 보존!)
    def clean_text_for_compare(text):
        # 괄호와 그 안의 내용만 제거 ([...], (...))
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        # 공백 제거 및 소문자화 (이제 알파벳/숫자 외의 문자도 살려둡니다)
        text = text.replace(" ", "").lower()
        return text

    # 2. 유사도 측정
    def get_similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

    # 3. 핵심 단어 교집합 (기준 완화: 1개만 겹쳐도 의심)
    def get_token_overlap(a, b):
        stop_words = {'university', 'college', 'school', 'program', 'of', 'the', 'and', 'for', 'in', '2025', '2026', 'summer', 'winter', 'session', '참가자', '모집', '공고', '안내'}
        
        # 띄어쓰기 기준으로 단어 분리
        tokens_a = set(a.split()) - stop_words
        tokens_b = set(b.split()) - stop_words
        
        if not tokens_a or not tokens_b: return 0
        
        intersection = tokens_a.intersection(tokens_b)
        return len(intersection)

    for _, row in yes_programs.iterrows():
        is_duplicate = False
        current_clean = clean_text_for_compare(row['title'])
        
        for existing in unique_programs:
            existing_clean = clean_text_for_compare(existing['title'])
            
            # [비교 1] 포함 관계
            cond1 = (current_clean in existing_clean) or (existing_clean in current_clean)
            
            # [비교 2] 유사도 기준을 0.6 -> 0.4로 대폭 낮춤 (조금만 비슷해도 합침)
            cond2 = get_similarity(current_clean, existing_clean) > 0.4
            
            # [비교 3] 핵심 단어가 1개 이상 겹치면 중복 간주 (Tübingen 하나만 겹쳐도 잡음)
            cond3 = get_token_overlap(row['title'].lower(), existing['title'].lower()) >= 1
            
            if cond1 or cond2 or cond3:
                is_duplicate = True
                
                # [합치기 전략]
                # 둘 다 OIA라면? -> 제목 긴 거(자세한 거) or 짧은 거(깔끔한 거) 선택
                # 여기선 제목이 '짧은 쪽'을 선택해서 깔끔하게 보이게 설정
                if len(row['title']) < len(existing['title']):
                    existing['title'] = row['title']
                    existing['link'] = row['link'] # 링크도 갱신
                
                # 만약 기존엔 이미지가 없었는데, 새것에 이미지가 있다면 이미지 업데이트
                if (pd.isna(existing.get('img_url')) or existing.get('img_url') == '') and (not pd.isna(row.get('img_url')) and row.get('img_url') != ''):
                    existing['img_url'] = row['img_url']

                break
        
        if not is_duplicate:
            unique_programs.append(row)
    # --- [알고리즘 끝] ---

    st.markdown(f"<h4 style='margin-bottom:20px;'>✨ AI가 엄선한 알짜배기 공지를 모았어요 ({len(unique_programs)}건)</h4>", unsafe_allow_html=True)

    if not unique_programs:
        st.info("현재 발견된 확실한 해외 프로그램이 없습니다.")
    else:
        # Grid Layout (가로 2개씩)
        for i in range(0, len(unique_programs), 2):
            cols = st.columns(2)
            batch = unique_programs[i : i+2]
            
            for idx, row in enumerate(batch):
                with cols[idx]:
                    flag = get_flag_icon(str(row['title']) + str(row['content']))
                    
                    card_html = f"""
                    <div class="program-card" style="height: 100%; min-height: 250px;">
                        <div class="flag-icon">{flag}</div>
                        <div class="card-content">
                            <span class="badge">{row['site_name']}</span>
                            <div class="card-title">{row['title']}</div>
                            <div class="period-info">
                                📅 {row['period']}
                            </div>
                            <div class="card-desc">
                                {row['reason']}
                            </div>
                        </div>
                        <a href="{row['link']}" target="_blank" class="action-btn">
                            공지 확인하기
                        </a>
                    </div>
                    """.replace('\n', '') 

                    st.markdown(card_html, unsafe_allow_html=True)





# ----------------------------------------------------------------
# [Tab 2] CHECK인 프로그램 (보내주신 코드 바탕으로 정렬만 수정)
# ----------------------------------------------------------------
with tab2:
    # 'CHECK' 상태인 데이터만 필터링
    check_programs = df[df['status'] == 'CHECK']
    
    # [유지] 사용자 멘트 및 헤더
    st.markdown(f"<h4 style='margin-bottom:20px;'>👀 놓치기 아쉬워서 이것도 챙겨왔어요 ({len(check_programs)}건)</h4>", unsafe_allow_html=True)
    st.caption("혹시 찾으시는 내용이 없을까 봐, 조금 더 넓은 범위로 찾아봤어요.")

    if check_programs.empty:
        st.success("애매한 공지사항이 없습니다! (AI가 분류를 아주 잘했거나, 해당되는 글이 없네요.)")
    else:
        # [수정] Grid Layout 적용을 위해 리스트로 변환
        rows_data = [row for _, row in check_programs.iterrows()]
        
        # 2개씩 끊어서 반복 (한 줄씩 그리기)
        for i in range(0, len(rows_data), 2):
            cols = st.columns(2) # 새로운 줄(Row) 생성
            batch = rows_data[i : i+2] # 데이터 2개 가져오기
            
            for idx, row in enumerate(batch):
                with cols[idx]: # 왼쪽(0) 또는 오른쪽(1) 칸
                    
                    # [유지] 국기 아이콘 및 카드 내용
                    flag = get_flag_icon(str(row['title']) + str(row['content']))
                    
                    # [유지] 보내주신 HTML 디자인 그대로 사용 
                    # (+ 높이 맞춤을 위해 style에 height: 100%만 살짝 추가했습니다)
                    card_html = f"""
                    <div class="program-card" style="height: 100%; min-height: 250px;">
                        <div class="flag-icon">{flag}</div>
                        <div class="card-content">
                            <span class="badge" style="background-color: #FFF3CD; color: #856404; border: 1px solid #FFEEBA;">
                                {row['site_name']} (확인필요)
                            </span>
                            <div class="card-title">{row['title']}</div>
                            <div class="period-info">
                                📅 {row['period']}
                            </div>
                            <div class="card-desc">
                                ❓ <b>AI 의견:</b> {row['reason']}
                            </div>
                        </div>
                        <a href="{row['link']}" target="_blank" class="action-btn" style="background-color: #6c757d;">
                            직접 확인하기
                        </a>
                    </div>
                    """.replace('\n', '') 

                    st.markdown(card_html, unsafe_allow_html=True)

# ----------------------------------------------------------------
# [Tab 3] AI 챗봇 상담
# ----------------------------------------------------------------
with tab3:
    st.markdown("### 🤖 무엇이든 물어보세요!")
    st.caption("현재 발견된 공지사항 내용을 바탕으로 AI가 답변해드립니다.")

    # 1. 채팅 기록 초기화 (처음 실행 시)
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "안녕하세요! 서울대 해외 프로그램 알림 봇입니다. 찾으시는 국가나 프로그램이 있으신가요?"}
        ]

    # 2. 이전 대화 내용 화면에 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3. 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요..."):
        # (1) 사용자 메시지 화면 표시 및 저장
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # (2) GPT 답변 생성
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # --- [핵심] DB 정보를 프롬프트에 주입 ---
            context_data = get_chatbot_context()
            
            system_prompt = f"""
            당신은 서울대학교 학생들의 글로벌 도전을 돕는 친절한 '해외 프로그램 멘토 AI'입니다.
            아래 제공된 [프로그램 목록]을 최우선으로 참고하여 답변하되, 학생의 준비를 돕기 위해 관련된 일반적인 지식도 활용하세요.

            [행동 지침]
            1. **프로그램 정보 매칭:** 사용자의 질문이 [프로그램 목록]에 있는 내용이라면, 정확한 정보를 요약해서 알려주세요.
            2. **배경 지식 활용 (확장):** 사용자가 프로그램과 연관된 '비자', '현지 문화', '물가', '준비물' 등을 물어보면, 목록에 정보가 없더라도 당신의 배경 지식을 활용해 친절하게 조언해주세요.
            - 단, 이때는 "비자나 현지 규정은 변동될 수 있으니 대사관 등 공식처에서 꼭 다시 확인해주세요."라는 주의사항을 덧붙여야 합니다.
            3. **연결하기:** 일반적인 조언을 해준 뒤에는, 자연스럽게 [프로그램 목록] 중 관련된 공지사항을 소개하거나 링크를 제공하세요. (예: "태국 비자는 보통 ~입니다. 마침 태국 관련 프로그램이 모집 중이니 확인해보세요!")
            4. **범위 제한:** 해외 파견이나 학교 생활과 전혀 관련 없는 질문(예: 연예인 가십, 수학 문제 등)에는 정중히 답변을 거절하고 프로그램 상담으로 유도하세요.
            5. **말투:** "챙겨드릴게요", "확인해보세요" 같은 친근하고 부드러운 해요체를 사용하고, 적절한 이모지를 섞어주세요.

            [프로그램 목록]
            {context_data}
            """
            
            # OpenAI API 호출
            try:
                stream = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt}
                    ] + [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=True
                )
                
                # 타자기 효과처럼 한 글자씩 출력
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
            
            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")
                full_response = "죄송합니다. 오류가 발생하여 답변할 수 없습니다."

        # (3) AI 답변 저장
        st.session_state.messages.append({"role": "assistant", "content": full_response})