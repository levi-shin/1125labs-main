import os
import requests
import feedparser
import yfinance as yf
from bs4 import BeautifulSoup

def get_market_data():
    """1. 환율, 금, 주가 지수 (Yahoo Finance)"""
    tickers = {
        "달러/원 환율": "KRW=X",
        "국제 금 (온스)": "GC=F",
        "S&P 500": "^GSPC",
        "나스닥": "^IXIC",
        "코스피 (야간/마감)": "^KS11"
    }
    
    market_lines = []
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change = ((price - prev_close) / prev_close) * 100
            sign = "+" if change > 0 else ""
            market_lines.append(f"• *{name}*: {price:,.2f} ({sign}{change:.2f}%)")
        except Exception:
            market_lines.append(f"• *{name}*: 데이터 수집 실패")
            
    return "\n".join(market_lines)


def get_gas_price():
    """2. 전국 평균 휘발유 가격 (오피넷 웹 크롤링)"""
    url = "https://www.opinet.co.kr/user/main/mainView.do"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        # 오피넷 메인화면 휘발유 평균 단가 추출
        gas_price = soup.select_one("#current_oil_price_1")
        if gas_price:
            return f"• *전국 평균 휘발유*: {gas_price.text.strip()}원/L"
        return "• *전국 평균 휘발유*: 확인 불가"
    except Exception:
        return "• *전국 평균 휘발유*: 수집 실패"


def get_top_news(limit=3):
    """3. 주요 경제 뉴스 3건 (구글 뉴스 경제 섹션 RSS)"""
    rss_url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    
    news_lines = []
    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link
        news_lines.append(f"• <{link}|{title}>")
        
    return "\n".join(news_lines) if news_lines else "• 수집된 뉴스가 없습니다."


def send_to_slack(message_text):
    """4. Slack Webhook 전송"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print(message_text)
        return

    payload = {"text": message_text}
    response = requests.post(webhook_url, json=payload, timeout=5)
    
    if response.status_code == 200:
        print("Slack 전송 성공")
    else:
        print(f"전송 실패: {response.status_code}, {response.text}")


def main():
    market_text = get_market_data()
    gas_text = get_gas_price()
    news_text = get_top_news()

    full_message = (
        "☀️ *오늘의 모닝 경제 브리핑*\n\n"
        "📊 *시장 지표 & 환율 & 금*\n"
        f"{market_text}\n\n"
        "⛽ *유가*\n"
        f"{gas_text}\n\n"
        "📰 *주요 경제 헤드라인*\n"
        f"{news_text}"
    )

    send_to_slack(full_message)


if __name__ == "__main__":
    main()
