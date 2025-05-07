#!/usr/bin/env python3
"""
Local Weather Counter with Preloaded Images & Random Shuffle

- 3초마다 사용자의 위치 기반 날씨 조회
- 날씨별 카운트 증가 (맑음:6~10, 흐림:3~5, 비:1~3)
- Nominatim reverse geocode로 위치명 동적 헤더/타이틀
- Wikipedia geosearch로 주변 이미지 최대 4개 가져와 클라이언트에서 랜덤 셔플
- 클라이언트에서 15초마다 미리 받아온 이미지 중 랜덤으로 배경 전환
- 날씨별 오버레이 이펙트, 카운트 플로팅 + 사운드
"""
from flask import Flask, jsonify, request
import requests, random

app = Flask(__name__)
counter = 0

WEATHER_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
WIKI_IMAGE_API = (
    "https://en.wikipedia.org/w/api.php?action=query&format=json"
    "&prop=pageimages&piprop=original"
    "&generator=geosearch&ggscoord={lat}%7C{lon}&ggsradius=10000&ggslimit=4"
)

@app.route('/counter')
def get_counter():
    global counter
    lat = request.args.get('lat', '37.5665')
    lon = request.args.get('lon', '126.9780')

    # 1) 날씨 조회 & 카운트 증가
    w = requests.get(WEATHER_URL.format(lat=lat, lon=lon), timeout=5).json().get('current_weather', {})
    code = w.get('weathercode', 1)
    if code == 0:
        main, inc = 'clear', random.randint(6,10)
    elif code in (1,2,3):
        main, inc = 'clouds', random.randint(3,5)
    else:
        main, inc = 'rain', random.randint(1,3)
    counter += inc

    # 2) Wikipedia 이미지 최대 4개 가져오기
    wiki = requests.get(WIKI_IMAGE_API.format(lat=lat, lon=lon), timeout=5).json()
    pages = wiki.get('query', {}).get('pages', {}).values()
    imgs = [p.get('original',{}).get('source') for p in pages if p.get('original')]
    random.shuffle(imgs)

    return jsonify(
        counter=counter,
        weather=main,
        image_urls=imgs  # 최대 4개의 URL 리스트
    )

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title id="page-title">날씨 멍</title>
<style>
  /* 기존 스타일 그대로 유지 */
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:100%;height:100%;overflow:hidden;font-family:'Segoe UI',sans-serif}
  #bg1,#bg2,#effect-overlay{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}
  #bg1,#bg2{background-size:cover;background-position:center;transition:opacity 1s ease-in-out}
  #bg1{z-index:-3;opacity:1}#bg2{z-index:-4;opacity:0}
  #effect-overlay{z-index:-2}
  .container{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);z-index:1;
    width:320px;padding:2rem;border-radius:1rem;box-shadow:0 8px 20px rgba(0,0,0,0.1);
    text-align:center;transition:background-color .5s;}
  #header-location{font-size:2rem;font-weight:bold;margin-bottom:.5rem}
  #header-status{font-size:2.5rem;font-weight:bold;color:#FF6F61;margin-bottom:1rem}
  #weather-icon{font-size:2.5rem;margin-bottom:.5rem}
  #counter{font-size:3rem;font-weight:bold;color:#FF6F61}
  .floating{position:absolute;font-size:2rem;color:#FF6F61;z-index:2;
    transition:all 1s ease-out;pointer-events:none}
  .effect-clear{animation:sunshine 3s infinite}
  @keyframes sunshine{0%{background:radial-gradient(circle,rgba(255,255,224,0.4)0%,transparent70%)}50%{background:radial-gradient(circle,rgba(255,249,196,0.6)0%,transparent70%)}100%{background:radial-gradient(circle,rgba(255,255,224,0.4)0%,transparent70%)}}
  .effect-rain{background-image:radial-gradient(rgba(255,255,255,0.3)1px,transparent1px);background-size:3px 10px;animation:rain .5s linear infinite}
  @keyframes rain{0%{background-position:0 0}100%{background-position:0 10px}}
  .effect-clouds{background:rgba(0,0,0,0.2)}
</style>
<script>
  let images = [], prev=0, lastBg=1, imgTs=0;
  const FETCH_INTERVAL = 3000;  // 3초마다 날씨&카운트 조회
  const BG_INTERVAL    = 15000; // 15초마다 배경 셔플

  function crossfade(url) {
    const now = Date.now();
    if (!imgTs || now - imgTs > BG_INTERVAL) {
      imgTs = now;
      const next = lastBg===1?2:1;
      document.getElementById('bg'+next).style.backgroundImage = `url('${url}')`;
      document.getElementById('bg'+next).style.opacity = 1;
      document.getElementById('bg'+lastBg).style.opacity = 0;
      lastBg = next;
    }
  }

  // (playDing, showFloating, applyEffects, reverseGeo는 그대로 유지)

  async function fetchWeather(lat,lon) {
    try {
      const r = await fetch(`/counter?lat=${lat}&lon=${lon}`);
      const d = await r.json();

      // 최초 호출 시 이미지 배열 설정 & 배경 시작
      if (!images.length && Array.isArray(d.image_urls)) {
        images = d.image_urls;
        if (images.length) {
          crossfade(images[0] + `?t=${Date.now()}`);
          setInterval(() => {
            const u = images[Math.floor(Math.random()*images.length)];
            crossfade(u + `?t=${Date.now()}`);
          }, BG_INTERVAL);
        }
      }

      const place = await reverseGeo(lat,lon);
      document.getElementById('header-location').innerText = place;
      document.getElementById('page-title').innerText      = `${place} 날씨 멍`;
      applyEffects(d.weather);
      document.getElementById('weather-icon').innerText    =
        d.weather==='clear'?'☀️':d.weather==='clouds'?'☁️':'🌧️';

      const cnt = d.counter;
      document.getElementById('counter').innerText = cnt;
      const inc = cnt - prev;
      if (inc>0) { playDing(); showFloating(inc); }
      prev = cnt;
    } catch(e) { console.error(e); }
  }

  function start() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(p => {
        const {latitude:lat, longitude:lon} = p.coords;
        fetchWeather(lat,lon);
        setInterval(()=>fetchWeather(lat,lon), FETCH_INTERVAL);
      });
    }
  }

  window.onload = start;
</script>
</head>
<body>
  <div id="bg1"></div><div id="bg2"></div><div id="effect-overlay"></div>
  <div class="container">
    <div id="header-location">Local</div>
    <div id="header-status">날씨 멍</div>
    <div id="weather-icon">☁️</div>
    <div id="counter">0</div>
  </div>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_PAGE

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
