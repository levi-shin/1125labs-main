import os
import requests
import feedparser
import yfinance as yf


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
    """3. 전국 평균 휘발유 가격 (오피넷/네이버 다중 경로 수집)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. 오피넷 메인 데이터 API (공개 엔드포인트)
    try:
        opinet_url = "https://www.opinet.co.kr/user/d anawa/d anawaSelect.do"  # 오피넷 시세 데이터
        res = requests.post(
            "https://www.opinet.co.kr/user/main/mainOilPrice.do",
            headers=headers,
            timeout=8,
            verify=False
        )
        if res.status_code == 200:
            import json
            data = res.json()
            # 보통휘발유(B027) 가격 추출
            for oil in data.get("oilPriceList", []):
                if oil.get("PRODCD") == "B027" or "휘발유" in oil.get("PROD_NM", ""):
                    price = f"{float(oil.get('PRICE', 0)):,.2f}"
                    diff = oil.get("DIFF", "0")
                    sign = "+" if float(diff) > 0 else ""
                    return f"• *전국 평균 휘발유*: {price}원/L ({sign}{diff}원)"
    except Exception:
        pass

    # 2. 다음(Daum) 금융 유가 API 백업 (해외 IP 차단 없음)
    try:
        daum_url = "https://finance.daum.net/api/market_index/oil/OIL_G001"
        daum_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://finance.daum.net/"
        }
        res = requests.get(daum_url, headers=daum_headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            price = data.get("tradePrice")
            change = data.get("changePrice")
            sign = "+" if data.get("change") == "RISE" else ("-" if data.get("change") == "FALL" else "")
            if price:
                return f"• *전국 평균 휘발유*: {price:,.2f}원/L ({sign}{change}원)"
    except Exception:
        pass

    # 3. 네이버 금융 단독 모바일 텍스트 파싱 백업
    try:
        n_url = "https://finance.naver.com/marketindex/oilDetail.naver?marketindexCd=OIL_G001"
        res = requests.get(n_url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        val = soup.select_one("em.no_today span.blind") or soup.select_one("div.head_info em")
        if val:
            return f"• *전국 평균 휘발유*: {val.text.strip()}원/L"
    except Exception:
        pass

    return "• *전국 평균 휘발유*: 데이터 갱신 대기 중"

def get_weather():
    """4. 오늘의 서울 날씨 (Open-Meteo 무료 API: 섭씨 기준)"""
    # 서울 좌표 (위도 37.5665, 경도 126.9780)
    url = "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code&timezone=Asia%2FTokyo"
    try:
        res = requests.get(url, timeout=5)
        data = res.json().get("current", {})
        temp = data.get("temperature_2m", 0)
        app_temp = data.get("apparent_temperature", 0)
        humidity = data.get("relative_humidity_2m", 0)
        code = data.get("weather_code", 0)

        # WMO 날씨 코드 한글 매핑
        weather_map = {
            0: "맑음 ☀️", 1: "대체로 맑음 🌤️", 2: "구름 조금 ⛅", 3: "흐림 ☁️",
            45: "안개 🌫️", 48: "안개 🌫️",
            51: "이슬비 🌧️", 53: "이슬비 🌧️", 55: "이슬비 🌧️",
            61: "약한 비 🌧️", 63: "비 🌧️", 65: "강한 비 🌧️",
            71: "약한 눈 🌨️", 73: "눈 🌨️", 75: "강한 눈 🌨️",
            80: "소나기 🌦️", 81: "소나기 🌦️", 82: "강한 소나기 ⛈️",
            95: "뇌우 ⚡"
        }
        status = weather_map.get(code, "맑음 ☀️")

        return f"• *서울 날씨*: {status} {temp:.1f}℃ (체감 {app_temp:.1f}℃), 습도 {humidity}%"
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
