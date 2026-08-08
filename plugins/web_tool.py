import re
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class WebSearchRequest(BaseModel):
    query: str = Field(..., description="搜索关键词")
    num_results: int = Field(5, ge=1, le=10, description="返回结果数量")


class WebFetchRequest(BaseModel):
    url: str = Field(..., description="目标网页 URL")
    include_images: bool = Field(False, description="是否提取图片链接")


class WebSearchResponse(BaseModel):
    results: list = Field(default_factory=list)
    error: Optional[str] = Field(None, description="搜索失败时的错误说明")
    details: list = Field(default_factory=list, description="各搜索源的错误详情")


class WebFetchResponse(BaseModel):
    url: str
    title: str
    text: str
    images: list = Field(default_factory=list)
    links: list = Field(default_factory=list)
    safe_check: dict = Field(default_factory=dict)


async def _fetch_url(url: str, timeout: float = 15.0) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def _extract_title(soup: BeautifulSoup) -> str:
    title = soup.find("title")
    return title.get_text(strip=True) if title else ""


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:2000])


def _extract_links(soup: BeautifulSoup, base_url: str) -> list:
    links = []
    for a in soup.find_all("a", href=True):
        href = urllib.parse.urljoin(base_url, a["href"])
        text = a.get_text(strip=True)
        if href.startswith("http"):
            links.append({"url": href, "text": text})
    return links[:50]


def _extract_images(soup: BeautifulSoup, base_url: str) -> list:
    images = []
    for img in soup.find_all("img", src=True):
        src = urllib.parse.urljoin(base_url, img["src"])
        if src.startswith("http"):
            images.append({"url": src, "alt": img.get("alt", "")})
    return images[:30]


async def _search_duckduckgo(query: str, num_results: int) -> list:
    """通过 DuckDuckGo HTML 版获取搜索结果。"""
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    html = await _fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select(".result")[:num_results]:
        a = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        if href.startswith("//"):
            href = "https:" + href
        results.append(
            {
                "title": a.get_text(strip=True),
                "url": href,
                "snippet": snippet.get_text(strip=True) if snippet else "",
            }
        )
    return results


async def _search_bing(query: str, num_results: int) -> list:
    """Bing 搜索备用。"""
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}"
    html = await _fetch_url(url, timeout=10.0)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Bing 结果通常位于 .b_algo
    for item in soup.select(".b_algo")[:num_results]:
        a = item.select_one("a")
        if not a:
            continue
        href = a.get("href", "")
        title = a.get_text(strip=True)
        snippet_elem = item.select_one(".b_caption p") or item.select_one("p")
        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
        if href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": snippet})
    return results


@router.post("/search", operation_id="web_search", response_model=WebSearchResponse)
async def web_search(req: WebSearchRequest):
    """网页增强搜索 / 关键词搜索"""
    errors = []
    try:
        results = await _search_duckduckgo(req.query, req.num_results)
        if results:
            return {"results": results}
    except Exception as exc:
        errors.append(f"DuckDuckGo: {type(exc).__name__}: {exc}")

    try:
        results = await _search_bing(req.query, req.num_results)
        if results:
            return {"results": results}
    except Exception as exc:
        errors.append(f"Bing: {type(exc).__name__}: {exc}")

    # 两个源都失败时返回空结果，避免元器调用中断
    return {
        "results": [],
        "error": "当前网络环境无法访问搜索引擎，请检查函数出口网络或稍后重试",
        "details": errors,
    }


@router.post("/fetch", operation_id="web_fetch", response_model=WebFetchResponse)
async def web_fetch(req: WebFetchRequest):
    """网页文本 / 图片 / 表格 / 链接提取与视觉理解摘要"""
    parsed = urllib.parse.urlparse(req.url)
    path_lower = parsed.path.lower()
    suspicious = ["exe", "zip", "rar", "bat", "cmd", "sh"]
    risky_ext = any(path_lower.endswith(f".{ext}") for ext in suspicious)
    try:
        html = await _fetch_url(req.url)
        soup = BeautifulSoup(html, "html.parser")
        title = _extract_title(soup)
        text = _extract_text(soup)
        links = _extract_links(soup, req.url)
        images = _extract_images(soup, req.url) if req.include_images else []
        return WebFetchResponse(
            url=req.url,
            title=title,
            text=text[:8000],
            images=images,
            links=links,
            safe_check={
                "reachable": True,
                "risk_score": 30 if risky_ext else 0,
                "risky_extension": risky_ext,
            },
        )
    except Exception as exc:
        # 不要抛 500，否则元器会判定工具调用失败。
        # 返回 200 并说明无法抓取，模型可改用搜索摘要继续回答。
        err_msg = f"无法获取页面内容（{type(exc).__name__}: {exc}）。请基于搜索结果摘要回答。"
        return WebFetchResponse(
            url=req.url,
            title="",
            text=err_msg,
            images=[],
            links=[],
            safe_check={
                "reachable": False,
                "risk_score": 30 if risky_ext else 0,
                "risky_extension": risky_ext,
            },
        )


@router.get("/safe-check", operation_id="web_safe_check")
async def web_safe_check(url: str = Query(..., description="待检测 URL")):
    """网页安全检测（基础黑名单 + 可达性检查）"""
    suspicious = ["exe", "zip", "rar", "bat", "cmd", "sh"]
    parsed = urllib.parse.urlparse(url)
    path_lower = parsed.path.lower()
    risky_ext = any(path_lower.endswith(f".{ext}") for ext in suspicious)
    try:
        await _fetch_url(url, timeout=5.0)
        reachable = True
    except Exception:
        reachable = False
    return {
        "url": url,
        "reachable": reachable,
        "risk_score": 30 if risky_ext else 0,
        "risky_extension": risky_ext,
    }
