#!/usr/bin/env python3
"""
Weather Meong Homepage

- 1초마다 사용자의 위치 기반 날씨 조회 (Open-Meteo, API 키 불필요)
- 날씨별 카운트 증가 (맑음:6~10, 흐림/구름:3~5, 비/눈:1~3)
- Nominatim reverse geocode로 위치명 동적 헤더
- 상단에 위치명, 그 아래에 '날씨 멍' 텍스트
- Wikipedia 또는 Unsplash 배경 이미지 15초마다 부드러운 크로스페이드
- 날씨별 오버레이 이펙트 (햇빛, 흐림, 비)
- 카운트 플로팅 이펙트 + 사운드

요구 패키지:
$ pip install flask requests
$ python weather_counter.py
"""
from flask import Flask, jsonify, request
import requests
import random

app = Flask(__name__)
counter = 0
current_weather = 'clouds'

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}&current_weather=true"
)
WIKI_IMAGE_URL = (
    "https://en.wikipedia.org/w/api.php?action=query&format=json"
    "&prop=pageimages&piprop=original"
    "&generator=geosearch&ggscoord={lat}%7C{lon}&ggsradius=10000&ggslimit=10"
)

@app.route('/counter')
def get_counter():
    global counter, current_weather
    lat = request.args.get('lat', '37.5665')
    lon = request.args.get('lon', '126.9780')
    # 날씨 조회
    data = requests.get(WEATHER_URL.format(lat=lat, lon=lon), timeout=5).json()
    code = data.get('current_weather', {}).get('weathercode', 1)
    if code == 0:
        main = 'clear'
    elif code in (1, 2, 3):
        main = 'clouds'
    else:
        main = 'rain'
    current_weather = main
    # 카운트 증가량
    if main == 'clear':
        inc = random.randint(6, 10)
    elif main == 'clouds':
        inc = random.randint(3, 5)
    else:
        inc = random.randint(1, 3)
    counter += inc
    # 배경 이미지 조회 (랜덤 선택)
    image_url = None
    try:
        wiki = requests.get(WIKI_IMAGE_URL.format(lat=lat, lon=lon), timeout=5).json()
        pages = wiki.get('query', {}).get('pages', {})
        if pages:
            selected = random.choice(list(pages.values()))
            image_url = selected.get('original', {}).get('source')
    except:
        image_url = None
    return jsonify(counter=counter, weather=current_weather, image_url=image_url)

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title id="page-title">날씨 멍</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    html, body { width:100%; height:100%; overflow:hidden; font-family:'Segoe UI',sans-serif; }
    #bg1, #bg2, #effect-overlay { position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; }
    #bg1, #bg2 { background-size:cover; background-position:center; transition:opacity 1s ease-in-out; }
    #bg1 { z-index:-3; opacity:1; } #bg2 { z-index:-4; opacity:0; }
    #effect-overlay { z-index:-2; }
    .container {
      position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
      z-index:1; width:320px; padding:2rem; border-radius:1rem;
      box-shadow:0 8px 20px rgba(0,0,0,0.1);
      text-align:center; transition:background-color .5s;
    }
    #header-location { font-size:2rem; margin-bottom:0.5rem; }
    #header-status {
      font-size:2.5rem; margin-bottom:1rem;
      color:#FF6F61; font-weight:bold;
    }
    #weather-icon { font-size:2.5rem; margin-bottom:0.5rem; }
    #counter { font-size:3rem; font-weight:bold; color:#FF6F61; }
    .floating {
      position:absolute; font-size:2rem; color:#FF6F61;
      z-index:2; transition:all 1s ease-out; pointer-events:none;
    }
    .effect-clear { animation:sunshine 3s infinite; }
    @keyframes sunshine {
      0% { background:radial-gradient(circle at center,rgba(255,255,224,0.4)0%,transparent70%); }
      50% { background:radial-gradient(circle at center,rgba(255,249,196,0.6)0%,transparent70%); }
      100% { background:radial-gradient(circle at center,rgba(255,255,224,0.4)0%,transparent70%); }
    }
    .effect-clouds { background:rgba(0,0,0,0.2); }
    .effect-rain { background-image:radial-gradient(rgba(255,255,255,0.3)1px,transparent1px); background-size:3px 10px; animation:rain .5s linear infinite; }
    @keyframes rain { 0% { background-position:0 0; } 100% { background-position:0 10px; } }
  </style>
  <script>
    let prev=0, lastBg=1, ts=0;
    function crossfade(url) {
      const now = Date.now();
      if (!ts || now - ts > 15000) {
        ts = now;
        const next = lastBg===1?2:1;
        const curr = document.getElementById('bg'+lastBg);
        const nxt = document.getElementById('bg'+next);
        nxt.style.backgroundImage = `url('${url}')`;
        nxt.style.opacity = 1;
        curr.style.opacity = 0;
        lastBg = next;
      }
    }
    function playDing() {
      const ctx=new (window.AudioContext||window.webkitAudioContext)(), o=ctx.createOscillator();
      o.type='sine'; o.frequency.setValueAtTime(1000,ctx.currentTime);
      o.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.1);
    }
    function showFloating(inc) {
      const el=document.createElement('div'); el.className='floating'; el.innerText='+'+inc;
      document.body.appendChild(el);
      const r=document.getElementById('counter').getBoundingClientRect();
      el.style.left = r.left+r.width/2+'px'; el.style.top = r.top+'px';
      el.style.transform='translate(-50%,-100%)';
      setTimeout(()=>{ el.style.top = r.top-30+'px'; el.style.opacity=0; },50);
      setTimeout(()=>el.remove(),1050);
    }
    function applyEffects(w) {
      const ov=document.getElementById('effect-overlay'); ov.className='';
      if (w==='clear') ov.classList.add('effect-clear');
      else if (w==='clouds') ov.classList.add('effect-clouds');
      else ov.classList.add('effect-rain');
      const c=document.querySelector('.container');
      if (w==='clear') c.style.backgroundColor='rgba(255,245,157,0.8)';
      else if (w==='clouds') c.style.backgroundColor='rgba(144,164,174,0.8)';
      else c.style.backgroundColor='rgba(144,202,249,0.8)';
    }
    async function reverseGeo(lat,lon) {
      try {
        const r = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`);
        const d = await r.json(); const a = d.address;
        return a.city||a.town||a.village||a.county||'현재위치';
      } catch { return '현재위치'; }
    }
    async function fetchData(lat,lon) {
      try {
        const res=await fetch(`/counter?lat=${lat}&lon=${lon}`);
        const d=await res.json();
        const now=Date.now();
        const bgUrl = d.image_url ? d.image_url+`?t=${now}` : `https://source.unsplash.com/1600x900/?${d.weather}&${now}`;
        crossfade(bgUrl);
        const place = await reverseGeo(lat,lon);
        document.getElementById('header-location').innerText = place;
        document.getElementById('header-status').innerText = '날씨 멍';
        applyEffects(d.weather);
        document.getElementById('weather-icon').innerText = d.weather==='clear'?'☀️':d.weather==='clouds'?'☁️':'🌧️';
        document.getElementById('counter').innerText = d.counter;
        const inc = d.counter - prev;
        if (inc>0) { playDing(); showFloating(inc); }
        prev = d.counter;
      } catch(e) { console.error(e); }
    }
    function start() {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(p=>{
          const lat=p.coords.latitude, lon=p.coords.longitude;
          fetchData(lat,lon);
          setInterval(()=>fetchData(lat,lon),1000);
        });
      }
    }
    window.onload = start;
  </script>
</head>
<body>
  <div id="bg1"></div><div id="bg2"></div><div id="effect-overlay"></div>
  <div class="container">
    <h1 id="header-location">현재위치</h1>
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
