import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import time
import urllib3
import pdfplumber
import io
import olefile  # <--- [추가] HWP 파싱용
import zlib     # <--- [추가] HWP 압축 해제용
import struct   # <--- [추가] 바이너리 해석용
import base64  # <--- [추가] 이미지를 GPT에게 보내기 위한 변환 도구
import sqlite3 # <--- [추가] DB 저장용 라이브러리


# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# [설정] API 키 입력
# ==========================================
# [변경] GitHub에 올릴 때는 이렇게 따옴표 안을 비워두세요
API_KEY = "" 

client = OpenAI(api_key=API_KEY)

# [추가] 봇 차단 방지용 헤더 (브라우저인 척 속임)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# [설정] 크롤링할 사이트 목록
# ==========================================
SITES = [
    {"name": "서울대 OIA", "url": "https://oia.snu.ac.kr/notice-all?combine=&page=0"},
    {"name": "서울대 OIA", "url": "https://oia.snu.ac.kr/notice-all?combine=&page=1"},
    {"name": "서울대 OIA", "url": "https://oia.snu.ac.kr/notice-all?combine=&page=2"},
    {"name": "자유전공학부", "url": "https://cls.snu.ac.kr/notice/?pageid=1&mod=list"},
    {"name": "자유전공학부", "url": "https://cls.snu.ac.kr/notice/?pageid=2&mod=list"},
    {"name": "서울대 SR", "url": "https://snusr.snu.ac.kr/community/notice?page=1"},
    {"name": "서울대 SR", "url": "https://snusr.snu.ac.kr/community/notice?page=2"},
    {"name": "인문대학", "url": "https://humanities.snu.ac.kr/community/notice"},
    {"name": "공과대학", "url": "https://eng.snu.ac.kr/snu/bbs/BMSR00004/list.do?menuNo=200176"},
    {"name": "자연과학대", "url": "https://science.snu.ac.kr/news/announcement"},
    {"name": "경영대학", "url": "https://cba.snu.ac.kr/newsroom/notice?sc=y"},
    {"name": "농업생명과학대", "url": "https://cals.snu.ac.kr/board/notice"},
    {"name": "사회과학대", "url": "https://social.snu.ac.kr/%ea%b3%b5%ec%a7%80%ec%82%ac%ed%95%ad/"},
    {"name": "사범대학", "url": "https://edu.snu.ac.kr/category/board_17_gn_ldca7if5_20201130072915/"},
    {"name": "음악대학", "url": "https://music.snu.ac.kr/notice"},
    {"name": "수의과대학", "url": "https://vet.snu.ac.kr/category/board-3-BL-8Piv9u51-20211029154329/"},
    {"name": "생활과학대", "url": "https://che.snu.ac.kr/category/board-35-GN-EKIrl47t-20210226142951/"},
    {"name": "간호대학", "url": "https://nursing.snu.ac.kr/board/notice"},
    {"name": "약학대학", "url": "https://snupharm.snu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/"},
    {"name": "치의학대학원", "url": "https://dentistry.snu.ac.kr/fnt/nac/selectNoticeList.do?bbsId=BBS_0000000000001"},
    {"name": "의과대학", "url": "https://medicine.snu.ac.kr/fnt/nac/selectNoticeList.do?bbsId=BBSMSTR_000000000001"},
    {"name": "학부대학", "url": "https://snuc.snu.ac.kr/%ea%b3%b5%ec%a7%80%ec%82%ac%ed%95%ad/?pageid=1&mod=list"},
    {"name": "학부대학", "url": "https://snuc.snu.ac.kr/%ea%b3%b5%ec%a7%80%ec%82%ac%ed%95%ad/?pageid=2&mod=list"}
]

EXCLUDE_KEYWORDS = [
    "Scholarship", "scholarship", "장학금", "교환학생", 
    "Exchange", "등록금", "수강신청", "졸업", "학위","장학","수시","정시","현역병","병역","군복무",
    "근로", "예비군", "휴학", "복학", "대출","기숙사","입학", "채용", "인턴", "채용", "취업","전시회","계절수업","계절학기"
    "LNL", "신입생", "편입", "교내활동", "동아리", "학생회", "총학생회","졸업생","동문","동창회","수험생","면접","논문","이수규정","박사학위", "석사학위"
    "셔틀버스","교통","주차","주차장","강의평가","시험기간",
    "학위복", "채용 공고", "고사장", "만족도 조사","입주자","연건학생생활관","인실","서연재","국가시험","LnL", "도서관", "교원 초빙", "다전공", "복수전공", "부전공"
]

def encode_image_to_base64(image_url):
    try:
        # headers=HEADERS 추가
        response = requests.get(image_url, headers=HEADERS, verify=False, timeout=5)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
    except:
        return None
    return None

def extract_text_from_hwp(hwp_url):
    """
    [신규 추가] HWP 파일의 내용을 텍스트로 추출하는 함수
    """
    try:
        response = requests.get(hwp_url, headers=HEADERS, verify=False, timeout=10)
        f = io.BytesIO(response.content)
        
        try:
            ole = olefile.OleFileIO(f)
        except:
            return "" 

        text = ""
        dirs = ole.listdir()
        sections = [d for d in dirs if d[0] == "BodyText"]
        
        # 섹션 순서대로 정렬 (Section0, Section1...)
        sections.sort(key=lambda x: int(x[1].replace('Section', '')))

        for section in sections:
            try:
                stream = ole.openstream(section)
                data = stream.read()
                
                # HWP는 내용을 zlib으로 압축해서 저장함 -> 압축 해제
                unpacked_data = zlib.decompress(data, -15)
                
                decoded_text = unpacked_data.decode('utf-16-le', errors='ignore')
                
                # (실제 HWP 바이너리 구조를 완벽히 파싱하려면 복잡하므로, 텍스트 덤프 방식 사용)
                # 텍스트 덩어리만 추출 (간이 방식)
                clean_text = ""
                for char in decoded_text:
                    if char.isprintable() or char in ['\n', '\t', ' ']:
                        clean_text += char
                
                text += clean_text + "\n"

            except Exception:
                continue
                
        return text.strip()

    except Exception as e:
        return f""


def extract_text_from_pdf(pdf_url):
    """ [기존 유지 + 페이지 전체 읽기 적용됨] """
    try:
        response = requests.get(pdf_url, verify=False, timeout=10)
        f = io.BytesIO(response.content)
        text = ""
        with pdfplumber.open(f) as pdf:
            for page in pdf.pages: 
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text.strip()
    except Exception:
        return ""


def get_full_content(url):
    try:
        response = requests.get(url, headers=HEADERS, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 본문 영역 찾기
        content_div = (
            soup.select_one('.board-view-con') or 
            soup.select_one('.view-content') or 
            soup.select_one('.bbs_view') or
            soup.select_one('.con_area') or
            soup.select_one('#board_view') or
            soup.select_one('.bo_v_con')
        )
        web_text = content_div.get_text(strip=True)[:1000] if content_div else ""
        search_area = content_div if content_div else soup

        # 2. 첨부파일(PDF, HWP) 처리
        files = search_area.select('a')
        file_text_list = []
        for f in files:
            href = f.get('href', '')
            text = f.get_text(strip=True)
            if 'privacy' in href.lower(): continue
            
            full_url = href
            if not href.startswith('http'):
                base_url = "/".join(url.split('/')[:3])
                full_url = base_url + href if href.startswith('/') else base_url + '/' + href
            
            extracted = ""
            if full_url.lower().endswith('.pdf'):
                extracted = extract_text_from_pdf(full_url)
            elif full_url.lower().endswith('.hwp'):
                extracted = extract_text_from_hwp(full_url)
            
            if len(extracted) > 10:
                file_text_list.append(f"--- [첨부파일: {text}] ---\n{extracted}")

        # 3. [추가된 부분] 본문 이미지(jpg, png) 찾기
        images = search_area.select('img')
        image_base64_list = []
        
        for img in images:
            src = img.get('src', '')
            # 로고나 아이콘 같은 쓸데없는 이미지 제외
            if not src or 'button' in src or 'icon' in src or 'logo' in src or 'common' in src: continue
            
            img_url = src
            if not src.startswith('http'):
                base_url = "/".join(url.split('/')[:3])
                img_url = base_url + src if src.startswith('/') else base_url + '/' + src
            
            # 이미지 변환해서 리스트에 담기
            base64_str = encode_image_to_base64(img_url)
            if base64_str:
                image_base64_list.append(base64_str)
                if len(image_base64_list) >= 3: break # 최대 3장만 (비용 절약)

        full_text_content = f"[웹 본문]\n{web_text}\n\n" + "\n".join(file_text_list)
        
        # 텍스트와 이미지 리스트를 같이 반환
        return full_text_content, image_base64_list

    except Exception:
        return "내용 확인 불가", []






def init_db():
    conn = sqlite3.connect('snu_programs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS programs
                 (link TEXT PRIMARY KEY, 
                  site_name TEXT, 
                  title TEXT, 
                  status TEXT, 
                  target TEXT, 
                  reason TEXT, 
                  period TEXT,  
                  content TEXT, 
                  crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP)''') 
    conn.commit()
    conn.close()





def save_to_db(site_name, title, link, status, target, reason, period, content):
    try:
        conn = sqlite3.connect('snu_programs.db')
        c = conn.cursor()
        # period 컬럼 추가됨
        c.execute('''INSERT OR REPLACE INTO programs 
                     (link, site_name, title, status, target, reason, period, content)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (link, site_name, title, status, target, reason, period, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"   💾 DB 저장 실패: {e}")





def analyze_program(title, content, images=[]): # <--- 인자에 images 추가됨
    """ LLM에게 판단 요청 (텍스트 + 이미지) """
    
    
    prompt_text = f"""
    You are an AI assistant for Seoul National University students.
    Your goal is to identify **"Short-term Overseas Programs"** from university notices.

    [Selection Criteria]
    1. **YES (Include)**:
       - Clearly stated as a short-term overseas program (Summer/Winter school, Field trip, Cultural exchange).
       - Duration: Less than 1 month.
       - Location: Outside Korea.
       
    2. **CHECK (Needs Confirmation)**:
       - **Ambiguous**: The title looks like an overseas program, but the content is missing, too short, or unclear.
       - **Image Only**: If the text is empty but there are attached images, check the images for details.
       - **Benefit of Doubt**: If you are 60-90% sure it's relevant but miss key details (like specific dates), choose [CHECK].

    3. **NO (Exclude)**:
       - Clearly Domestic (Korea).
       - Long-term Exchange (Semester/Year).
       - Pure Job/Internship/Scholarship without cultural element.

    [Input Data]
    Title: {title}
    Content Summary: {content}

    [Output Instructions]
    - **Response Format**:
      판단: [YES] or [NO] or [CHECK]
      대상: (Target audience)
      기간: (Program Date, e.g., "2024.01.15 ~ 01.30" or "공지 참조")
      요약: (Please summarize the provided text into 1 to 3 polite Korean sentences describing what the program is. Focus on the core nature and purpose of the activity. Do not include specific details about dates or target audience.)
    """

    # [변경된 부분] GPT에게 텍스트와 이미지를 같이 보내는 규격
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Follow the output format strictly."},
        {
            "role": "user", 
            "content": [{"type": "text", "text": prompt_text}] # 텍스트 추가
        }
    ]

    # 이미지가 있으면 메시지에 이미지 추가
    for base64_img in images:
        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_img}"
            }
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Vision은 gpt-4o 필수
            messages=messages,
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"판단: [CHECK]\n대상: 확인 불가\n이유: API 에러 ({e})"





def find_best_title_link(row, base_url):
    """ 가장 제목스러운 링크 찾기 """
    links = row.select('a')
    best_link = None
    best_text = ""

    for link in links:
        text = link.get_text(strip=True)
        href = link.get('href', '')
        
        if len(text) < 4: continue
        if any(ext in href.lower() for ext in ['.pdf', '.hwp', '.zip', 'download']): continue
            
        if len(text) > len(best_text):
            best_text = text
            best_link = href

    if not best_link: return None, None

    if not best_link.startswith('http'):
        domain = "/".join(base_url.split('/')[:3])
        if best_link.startswith('/'):
            best_link = domain + best_link
        else:
            best_link = domain + '/' + best_link

    return best_text, best_link





def crawl_site(site_info):
    name = site_info['name']
    url = site_info['url']
    
    print(f"\n>>> 🏫 [{name}] 크롤링 시작...")
    
    try:
        # headers=HEADERS 추가 (봇 차단 회피)
        response = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = []
        
        # [게시판 구조 찾기]
        rows = soup.select('tbody tr')
        if not rows:
            rows = soup.select('table tr')
            rows = [r for r in rows if r.select('td')]
        if not rows:
            rows = (
                soup.select('li.list_item') or 
                soup.select('.board-list li') or 
                soup.select('.list_board li') or
                soup.select('.notice_list li') or
                soup.select('ul.board_list li')
            )

        print(f"   ㄴ 게시글 {len(rows)}개 스캔 시작")
        
        processed = 0
        for row in rows:
            if processed >= 20: break 
            
            title, link = find_best_title_link(row, url)
            if not title: continue

            # [1단계: 제목 필터링]
            if any(k in title for k in EXCLUDE_KEYWORDS) or any(k in title.lower() for k in ["scholarship", "exchange"]):
                print(f"   🚫 [즉시 제외] {title}")
                processed += 1
                continue

            print(f"   🔍 분석 중: {title}")
            
            full_content, images = get_full_content(link)        
            result = analyze_program(title, full_content, images) 
            
            # [결과 파싱 수정]
            lines = result.split('\n')
            status = "NO"
            target = "확인 필요"
            reason = ""     # 기본값
            period = "공지 참조"

            for line in lines:
                if line.startswith("판단:"):
                    if "YES" in line: status = "YES"
                    elif "CHECK" in line: status = "CHECK"
                
                # '대상' 파싱 (공백이나 * 등 제거)
                if "대상:" in line:
                    target = line.split("대상:")[-1].strip().strip("*")
                
                # '기간' 파싱
                if "기간:" in line:
                    period = line.split("기간:")[-1].strip().strip("*")
                
                # [여기가 핵심 수정] GPT는 '요약:'이라고 말하므로 '요약'을 찾아야 합니다.
                if "요약:" in line:
                    reason = line.split("요약:")[-1].strip().strip("*")
                # 혹시 '이유:'라고 말했을 수도 있으니 대비
                elif "이유:" in line:
                    reason = line.split("이유:")[-1].strip().strip("*")

            # [결과 출력]
            if status == "YES":
                print(f"   🎉 [발견!] {title}")
                print(f"       👉 대상: {target}")
                print(f"       👉 이유: {reason}")
            elif status == "CHECK":
                print(f"   🤔 [확인 필요] {title}")
                print(f"       👉 사유: {reason}")
            else:
                print(f"       ❌ [탈락] {reason}")

            # ========================================================
            # [핵심] DB에 저장하기 (YES, CHECK, NO 모두 저장)
            # ========================================================
            save_to_db(name, title, link, status, target, reason, period, full_content)
            # ========================================================
            
            processed += 1
            time.sleep(1)

    except Exception as e:
        print(f"   🚨 에러 발생: {e}")






if __name__ == "__main__":
    init_db()  # <--- 프로그램 시작 전 DB 초기화
    print("=== [PDF/Vision 분석 + DB 저장] 서울대 해외 프로그램 크롤러 ===")
    
    for site in SITES:
        crawl_site(site)
        print("-" * 60)