# 간단한 로컬 검색 기반 채팅 AI

이 프로젝트는 DuckDuckGo 검색(ddgs)로 URL을 찾고, requests + BeautifulSoup로 웹페이지를 스크래핑한 후 로컬에서 동작하는 llama.cpp로 답변을 생성하는 간단한 CLI 애플리케이션입니다. 
테스트 실험 학습용.

## 주요 기능
- DuckDuckGo 텍스트 검색으로 관련 URL 탐색 (ddgs 라이브러리 사용, 미설치 시 검색 결과가 비어있을 수 있음)
- requests + BeautifulSoup로 페이지 본문 스크래핑 (스크립트/스타일/헤더/푸터 제거)
- 로컬 LLM 서버에 OpenAI 호환 Chat Completions 요청으로 응답 생성
- 검색어 자동 생성(LLM 보조), 상위 URL 병합 요약, 한국어 답변 강제

- 스크랩 8000자로 제한되있고 무조건 검색하는걸로 일단 구현함 사용하는 ai가 판단을 잘 못해서.. 그리고 컨텍스트 제한 때문에 나눠서 읽던지(ai에 보내던지) 그래야 할지도 

## 설치 방법

1. 가상환경 생성 및 활성화

   Windows (cmd):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   Windows (PowerShell):
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

   Linux/Mac:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```
권장 요구 패키지: requests, beautifulsoup4, ddgs, python-dotenv
```