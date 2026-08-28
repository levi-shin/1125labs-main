import os
import requests
import feedparser
import yfinance as yf
from bs4 import BeautifulSoup


def get_market_data():
    """1. 환율, 금, 주가지수, 가상자산, 원자재, 국채금리 (Yahoo Finance)"""
    tickers = {
        # 통화 & 금리
        "달러/원 환율": "KRW=X",
        "미국 10년물 국채금리": "^TNX",
        # 주가지수 & 코인
        "S&P 500": "^GSPC",
        "나스닥": "^IXIC",
        "코스피 (마감)": "^KS11",
        "비트코인 (원화)": "BTC-KRW",
        # 원자재 & 에너지
        "국제 금 (온스)": "GC=F",
        "WTI 국제유가 (배럴)": "CL=F",
        "구리 (파운드)": "HG=F"
    }

    lines = []
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change = ((price - prev_close) / prev_close) * 100
            sign = "+" if change > 0 else ""
            
            # 국채금리는 % 단위이므로 다르게 표기
            if symbol == "^TNX":
                lines.append(f"• *{name}*: {price:.2f}% ({sign}{change:.2f}%)")
            else:
                lines.append(f"• *{name}*: {price:,.2f} ({sign}{change:.2f}%)")
        except Exception:
            lines.append(f"• *{name}*: 데이터 수집 실패")

    return "\n".join(lines)


def get_fear_and_greed():
    """2. 공포 & 탐욕 지수 (CNN Fear & Greed API)"""
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        score = int(round(data["fear_and_greed"]["score"]))
        rating = data["fear_and_greed"]["rating"].capitalize()
        
        # 한글 변환
        rating_ko = {
            "Extreme fear": "극단적 공포 🥶",
            "Fear": "공포 😨",
            "Neutral": "중립 😐",
            "Greed": "탐욕 😏",
            "Extreme greed": "극단적 탐욕 🔥"
        }.get(rating, rating)

        return f"• *CNN 공포·탐욕 지수*: {score}점 ({rating_ko})"
    except Exception:
        return "• *CNN 공포·탐욕 지수*: 수집 실패"


def get_gas_price():
    """3. 전국 평균 휘발유 가격 (네이버 증권 시장지표 크롤링)"""
    url = "https://finance.naver.com/marketindex/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        
        oil_item = soup.select_one("a.head.oil_gas span.value")
        if oil_item:
            return f"• *전국 평균 휘발유*: {oil_item.text.strip()}원/L"

        for item in soup.select("div.market1 ul.data_list li"):
            title = item.select_one("span.blind")
            if title and "휘발유" in title.text:
                val = item.select_one("span.value").text.strip()
                return f"• *전국 평균 휘발유*: {val}원/L"

        return "• *전국 평균 휘발유*: 확인 불가"
    except Exception:
        return "• *전국 평균 휘발유*: 수집 실패"


def get_weather():
    """4. 오늘의 서울 날씨 (wttr.in)"""
    url = "https://ko.wttr.in/Seoul?format=%c+%C,+%t+(체감+%f),+습도+%h"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return f"• *서울 날씨*: {res.text.strip()}"
        return "• *서울 날씨*: 수집 실패"
    except Exception:
        return "• *서울 날씨*: 수집 실패"


def get_top_news(limit=3):
    """5. 주요 경제 뉴스 (구글 뉴스 경제 RSS)"""
    rss_url = "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)

    news_lines = []
    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link
        news_lines.append(f"• <{link}|{title}>")

    return "\n".join(news_lines) if news_lines else "• 수집된 뉴스가 없습니다."


def send_to_slack(message_text):
    """6. Slack Webhook 전송"""
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
    sentiment_text = get_fear_and_greed()
    gas_text = get_gas_price()
    weather_text = get_weather()
    news_text = get_top_news()

    full_message = (
        "☀️ *오늘의 모닝 통합 브리핑*\n\n"
        "🌤️ *오늘의 날씨*\n"
        f"{weather_text}\n\n"
        "📊 *시장 지표 & 원자재 & 금리*\n"
        f"{market_text}\n\n"
        "🧠 *시장 심리*\n"
        f"{sentiment_text}\n\n"
        "⛽ *국내 유가*\n"
        f"{gas_text}\n\n"
        "📰 *주요 경제 헤드라인*\n"
        f"{news_text}"
    )

    send_to_slack(full_message)


if __name__ == "__main__":
    main()
