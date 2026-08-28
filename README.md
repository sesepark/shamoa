# 샤모아 — 서울대 해외 프로그램 알리미

서울대학교의 해외 파견·교환 프로그램 정보를 한곳에서 찾아보고, 조건에 맞는 프로그램을
추천받을 수 있게 만든 Streamlit 웹 앱입니다. 수업 최종 프로젝트로 만들었습니다. (2025-12)

## 기능

- 프로그램 목록을 카드 형태로 탐색하고 지역·기간·언어 조건으로 좁혀 봅니다.
- SQLite에 정리한 프로그램 데이터(`snu_programs.db`)를 기반으로 조회합니다.
- LLM에 질문해 상황에 맞는 프로그램을 추천받을 수 있습니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

OpenAI API 키는 코드에 넣지 않고 Streamlit secrets로 주입합니다.

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "..."
```

## 구성

```
app.py            Streamlit 앱 (UI, 검색·필터, 추천)
final_project.py  데이터 수집·정리 스크립트
snu_programs.db   프로그램 데이터 (SQLite)
```
