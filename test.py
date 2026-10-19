import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    # 正常标识自己，不伪造、不轮换
    "User-Agent": "MyCompliantBot/1.0 (contact: you@example.com)"
}

def check_robots(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # 读不到 robots 时不等于可以乱爬，建议人工确认
        print(f"[警告] 无法读取 {robots_url}，请人工确认条款")
        return False
    return rp.can_fetch(HEADERS["User-Agent"], url)def looks_like_anti_bot(resp: httpx.Response) -> str | None:
    text = resp.text.lower()
    final_url = str(resp.url).lower()

    if resp.status_code == 429:
        return "触发频率限制 429"
    if resp.status_code in (403, 503):
        return f"可能被反爬拦截 {resp.status_code}"
    if "captcha" in text or "验证码" in text or "人机验证" in text:
        return "出现验证码/人机验证"
    if "login" in final_url or "signin" in final_url or "登录" in text[:2000]:
        return "被重定向到登录墙"
    if "access denied" in text or "forbidden" in text:
        return "访问被拒绝"
    return None

def fetch(url: str, retries: int = 3) -> str:
    if not check_robots(url):
        raise PermissionError(f"robots.txt 不允许或无法确认: {url}")

    for i in range(retries):
        try:
            resp = httpx.get(
                url,
                headers=HEADERS,
                timeout=15,
                follow_redirects=True
)
            reason = looks_like_anti_bot(resp)
            if reason:
                raise RuntimeError(f"检测到反爬信号：{reason}。停止抓取，请走官方 API 或申请授权。")
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, RuntimeError) as e:
            if i == retries - 1:
                raise
            wait = 2 ** i
            print(f"[重试] {e}，等待 {wait}s")
            time.sleep(wait)

def parse(html: str):
    soup = BeautifulSoup(html, "lxml")
    return [h.get_text(strip=True) for h in soup.select("h1, h2")]

if __name__ == "__main__":
    url = "https://example.com/public-page"
    time.sleep(1)  # 限速
    html = fetch(url)
    print(parse(html))

