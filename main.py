"""
Search (DuckDuckGo) -> scrape URLs (requests + BeautifulSoup) -> answer with local LLM.
No Tavily, no LlamaIndex; Python web scraping only.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:8080").rstrip("/")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama")
LLAMA_TIMEOUT = int(os.getenv("LLAMA_TIMEOUT", "600"))
MAX_SCRAPE_URLS = int(os.getenv("MAX_SCRAPE_URLS", "3"))
MAX_CHARS_PER_PAGE = int(os.getenv("MAX_CHARS_PER_PAGE", "8000"))
# Max characters to show per URL when printing scraped content (full text still sent to LLM)
PRINT_SCRAPED_PREVIEW = int(os.getenv("PRINT_SCRAPED_PREVIEW", "600"))

def search_urls(query: str, max_results: int = 5) -> list[dict]:
    """Return list of {title, href, body} from DuckDuckGo text search."""
    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=max_results, backend="duckduckgo"))
        return [{"title": r.get("title", ""), "href": r.get("href", ""), "body": r.get("body", "")} for r in results if r.get("href")]
    except Exception:
        return []


def scrape_url(url: str, max_chars: int = MAX_CHARS_PER_PAGE) -> str:
    """Fetch URL and return plain text (strip scripts, styles)."""
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars] if len(text) > max_chars else text
    except Exception:
        return ""


def llm_suggest_search_queries(user_question: str, max_queries: int = 3) -> list[str]:
    """Ask LLM to suggest search queries for the user question; return list of query strings."""
    system = (
        "You are a search query assistant. Given a user question, output 1 to 3 short search queries "
        "that would find web pages that directly answer it. Use the same language as the question or English. "
        "Output only the search queries, one per line. No numbering, no explanation."
    )
    out = llama_chat(system, user_question)
    if not out or out.startswith("LLM "):
        return [user_question]
    lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
    return lines[:max_queries] if lines else [user_question]


def gather_web_context(search_query: str) -> str:
    """Search with given query, then scrape top URLs; return combined context text."""
    results = search_urls(search_query, max_results=MAX_SCRAPE_URLS + 2)
    parts = []
    for r in results[:MAX_SCRAPE_URLS]:
        url = r.get("href", "").strip()
        if not url or not url.startswith("http"):
            continue
        title = r.get("title", "")
        body_snippet = r.get("body", "")
        scraped = scrape_url(url)
        if scraped:
            parts.append(f"[{title}]\nURL: {url}\n{scraped}")
        else:
            parts.append(f"[{title}]\nURL: {url}\n{body_snippet}")
    return "\n\n---\n\n".join(parts) if parts else ""


def llama_chat(system_content: str, user_content: str) -> str:
    """POST to local llama server (OpenAI-compatible); return assistant text."""
    url = f"{LLAMA_SERVER_URL}/v1/chat/completions"
    body = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=LLAMA_TIMEOUT) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
        return (obj.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except HTTPError as e:
        return f"LLM 서버 오류 (HTTP {e.code}): {e.read().decode('utf-8', errors='replace')[:300]}"
    except URLError as e:
        return f"LLM 연결 실패: {e.reason}"


def answer_with_web(user_question: str) -> str:
    """Always: suggest search queries -> search + scrape -> answer in Korean."""
    queries = llm_suggest_search_queries(user_question)
    print(f"   검색어: {queries}")
    seen_urls = set()
    all_parts = []
    for q in queries:
        results = search_urls(q, max_results=MAX_SCRAPE_URLS + 2)
        for r in results[:MAX_SCRAPE_URLS]:
            url = r.get("href", "").strip()
            if not url or not url.startswith("http") or url in seen_urls:
                continue
            seen_urls.add(url)
            title, body_snippet = r.get("title", ""), r.get("body", "")
            scraped = scrape_url(url)
            text = scraped if scraped else body_snippet
            if text:
                all_parts.append({"title": title, "url": url, "text": text})
            if len(all_parts) >= MAX_SCRAPE_URLS * 2:
                break
        if len(all_parts) >= MAX_SCRAPE_URLS * 2:
            break

    for i, part in enumerate(all_parts, 1):
        sep = "=" * 50
        print(f"\n{sep}\n[스크랩 {i}] {part['title']}\n  URL: {part['url']}\n{'-' * 50}")
        preview = part["text"][:PRINT_SCRAPED_PREVIEW]
        if len(part["text"]) > PRINT_SCRAPED_PREVIEW:
            preview += "..."
        print(preview)
        print(sep)
    if all_parts:
        print()

    context = ""
    if all_parts:
        context = "\n\n---\n\n".join(
            f"[{p['title']}]\nURL: {p['url']}\n{p['text']}" for p in all_parts
        )
    korean_rule = "You must answer only in Korean (한국어). "
    if context:
        system = (
            korean_rule
            + "Answer the question using ONLY the scraped web content below. Extract and summarize relevant information; combine content from multiple pages when needed. "
            "If only partial or related information is available, answer based on it and state that it is from the provided pages."
        )
        user_content = f"Web content:\n{context}\n\nUser question: {user_question}"
    else:
        system = korean_rule + "Answer the question concisely."
        user_content = user_question
    return llama_chat(system, user_content)



def main() -> None:
    print("=" * 60)
    print("🤖 인터넷 검색 AI (웹 스크래핑 + 로컬 LLM)")
    print("=" * 60)
    print(f"\n📍 LLM: {LLAMA_SERVER_URL}")
    print("   검색: DuckDuckGo → URL 스크래핑 (requests + BeautifulSoup)")
    print(f"   스크래핑: 상위 {MAX_SCRAPE_URLS}개 URL, 페이지당 최대 {MAX_CHARS_PER_PAGE}자")
    print("\n💡 질문 입력 시 LLM이 검색어를 정한 뒤 검색·스크래핑해 답변합니다. 종료: quit / exit / 종료 / q")
    print("=" * 60)
    print()

    count = 0
    while True:
        try:
            print()
            user_input = input("❓ 질문: ").strip()
            if user_input.lower() in ("quit", "exit", "종료", "q"):
                print("\n👋 종료합니다.")
                break
            if not user_input:
                print("⚠️  질문을 입력해주세요.")
                continue
            count += 1
            print("\n🔍 LLM 검색어 생성 → 검색·스크래핑 → 답변 생성 중...")
            print("-" * 60)
            answer = answer_with_web(user_input)
            print(answer)
            print("-" * 60)
            print(f"📊 질문 수: {count}")
        except KeyboardInterrupt:
            print("\n\n👋 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류: {e}")


if __name__ == "__main__":
    main()
