# -*- coding: utf-8 -*-
"""로컬 상품 추출기 (실제 크롬 사용 = 봇차단 우회) — 어떤 URL이든 동작하게 범용화
사용법: python extract.py "https://..."
특징:
  · 전용 프로필(chrome-profile)에 로그인 저장 → 한 번 로그인하면 계속 유지
  · 로그인 벽 감지 시 최대 2분 대기(그 사이 직접 로그인하면 이어서 진행)
  · 모든 iframe(네이버 se-viewer 상세 등) + 배경이미지 + lazy속성까지 수집
  · 네이버 스마트스토어/브랜드스토어는 내부 API로 상세이미지까지 확보
결과: 같은 폴더의 data.json (스튜디오가 자동 로드)
"""
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
PROFILE = ROOT / "chrome-profile"
OUT = ROOT / "data.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

BAD = re.compile(r"logo|favicon|sprite|ico_|btn_|arrow|bullet|blank\.|1x1|pixel|"
                 r"sp_|badge_pc|gnb|npay_|loading|placeholder|/ico/|wmark|myInfo|"
                 r"/static/common/|ncaptcha|adcr|nid\.naver|doubleclick|"
                 r"googlesyndication|googleadservices|facebook\.com|analytics", re.I)
GOODHOST = re.compile(r"phinf|pstatic|cloudfront|naver|akamaized|cafe24|godo|"
                      r"shopify|amazonaws|ktcdn|imweb|makeshop|sixshop|"
                      r"kakaocdn|kakao|daumcdn|daum|t1\.|cdn|storyblok|"
                      r"objectstorage|ncloud|scdn|image", re.I)
EXTS = re.compile(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", re.I)


def clean(u):
    if not u or u.startswith("data:") or u.startswith("blob:"):
        return None
    if BAD.search(u):
        return None
    # 결제/추천 잡티 + 상품CDN이 아닌 phinf (브라우저에서 안 열림) 제외
    if re.search(r"checkout\.phinf|dthumb|service=selective|g-selected|/selective/", u, re.I):
        return None
    if re.search(r"phinf\.pstatic\.net", u) and not re.search(r"shop-phinf\.pstatic\.net", u):
        return None
    # 네이버 type 파라미터는 세로로 긴 상세컷을 축소시킴(o1000→높이1000) → 제거해서 원본 크기로
    u = re.sub(r"([?&])type=[^&]*(&)?", lambda m: (m.group(1) if m.group(2) else ""), u)
    if not EXTS.search(u) and not GOODHOST.search(u):
        return None
    return u


COLLECT_JS = r"""() => {
  const out=[];
  const junkUrl=/commerce_ui|\/assets\/|default_fallback|familymark|isolation|badge|promo|custom_tab|product_detail_banner|logo|ico_|gnb|_foot|_head|sp_|icon_|kamp-thumb|snapshot/i;
  const junkCls=/item_product|area_thumb|_head|_foot|info_store|tit_logo|mark_info|badge|corp_info|list_notice|review|recommend|related/i;
  const good=/phinf|pstatic|cloudfront|naver|akamaized|cafe24|godo|shopify|amazonaws|ktcdn|imweb|makeshop|sixshop|kakaocdn|kakao|daumcdn|daum|t1\.|storyblok|objectstorage|ncloud|scdn/i;
  const seen=new Set();
  const unwrap=u=>{const m=u.match(/[?&]fname=([^&]+)/);if(m&&u.indexOf('/thumb/')>=0){try{const o=decodeURIComponent(m[1]);if(/^https?:/i.test(o))return o;}catch(e){}}return u;};
  const push=(raw,w,h,cls)=>{
    if(!raw)return;
    if(/^data:|^blob:/i.test(raw))return;
    let u=unwrap(raw);
    u=u.replace(/([?&])type=[^&]*(&)?/g,(m,a,b)=>b?a:'');
    if(seen.has(u))return;
    // phinf.pstatic.net 중 상품CDN(shop-phinf)이 아니면 결제/추천잡티 → 제외 (브라우저에서도 안 열림)
    if(/phinf\.pstatic\.net/.test(u)&&!/shop-phinf\.pstatic\.net/.test(u))return;
    if(/dthumb|service=selective|g-selected|\/checkout\.phinf\/|\/selective\//i.test(u))return;
    if(!/\.(jpg|jpeg|png|webp|gif)(\?|$)/i.test(u)&&!good.test(u)&&!(w>=300||h>=300))return;
    if(junkUrl.test(u))return;
    const detail=/detail/i.test(cls)||/\/editor\//i.test(u)||(w&&h&&h/w>2.5);
    if(junkCls.test(cls)&&!detail)return;
    seen.add(u);out.push({u:u,w:w||0,h:h||0,detail:detail});
  };
  const abs=v=>{try{return new URL(v,location.href).href;}catch(e){return '';}};
  const clsOf=el=>{let a=el,p=[];for(let i=0;i<7&&a;i++){const c=a.className;if(c&&typeof c==='string')p.push(c);a=a.parentElement;}return p.join(' ');};
  document.querySelectorAll('img').forEach(im=>{
    const cls=clsOf(im), w=im.naturalWidth||0, h=im.naturalHeight||0;
    ['src','data-src','data-original','data-lazy','data-lazy-src','data-original-src','data-url','data-image','data-img','data-org','data-full'].forEach(k=>{const v=im.getAttribute(k);if(v)push(abs(v),w,h,cls);});
    const ss=im.getAttribute('srcset')||im.getAttribute('data-srcset');
    if(ss)ss.split(',').forEach(p=>{const u=p.trim().split(' ')[0];push(abs(u),w,h,cls);});
  });
  document.querySelectorAll('source').forEach(s=>{
    const cls=clsOf(s);
    const ss=s.getAttribute('srcset')||s.getAttribute('data-srcset');
    if(ss)ss.split(',').forEach(p=>{const u=p.trim().split(' ')[0];push(abs(u),0,0,cls);});
    const v=s.getAttribute('src');if(v)push(abs(v),0,0,cls);
  });
  try{const og=document.querySelector('meta[property="og:image"]');if(og&&og.content)push(abs(og.content),0,0,'og');}catch(e){}
  try{
    let n=0;
    document.querySelectorAll('*').forEach(el=>{
      if(n++>4000)return;
      const bg=getComputedStyle(el).backgroundImage;
      if(bg&&bg.indexOf('url(')>=0){const cls=clsOf(el);const re=/url\(["']?([^"')]+)["']?\)/g;let m;while((m=re.exec(bg)))push(abs(m[1]),0,0,cls);}
    });
  }catch(e){}
  return out;
}"""


def collect_all(pg):
    imgs = []
    for fr in pg.frames:
        try:
            imgs += fr.evaluate(COLLECT_JS) or []
        except Exception:
            pass
    return imgs


def click_more(pg):
    """상세 펼치기 버튼만 안전하게 클릭. 다른 페이지로 이탈하면 즉시 되돌린다."""
    labs = ["상품정보 더보기", "상세정보 더보기", "상세정보 펼치기", "상품정보 펼치기",
            "정보 더보기", "상세 더보기", "내용 더보기", "펼쳐보기"]
    for fr in pg.frames:
        for lab in labs:
            try:
                els = fr.query_selector_all(f"button:has-text('{lab}')")
            except Exception:
                els = []
            for el in els[:2]:
                try:
                    before = pg.url
                    el.click(timeout=700)
                    pg.wait_for_timeout(600)
                    if pg.url != before:            # 링크였음 → 이탈 복구
                        try:
                            pg.go_back(timeout=6000)
                            pg.wait_for_timeout(900)
                        except Exception:
                            pg.goto(before, timeout=20000, wait_until="domcontentloaded")
                except Exception:
                    pass


SCROLL_JS = """() => {
  try{ window.scrollBy(0, Math.max(800, innerHeight*0.95)); }catch(e){}
  try{
    document.querySelectorAll('div,section,main,ul').forEach(e=>{
      try{ if(e.scrollHeight>e.clientHeight+300 && e.clientHeight>280) e.scrollTop=e.scrollHeight; }catch(x){}
    });
  }catch(e){}
}"""


def scroll_all(pg, rounds=16):
    for _ in range(rounds):
        for fr in pg.frames:
            try:
                fr.evaluate(SCROLL_JS)
            except Exception:
                pass
        pg.wait_for_timeout(480)
    try:
        pg.evaluate("window.scrollTo(0,0)")
    except Exception:
        pass
    pg.wait_for_timeout(700)


def human_scroll(pg, rounds=30):
    """마우스 휠을 불규칙한 속도/간격으로 굴려 사람처럼 스크롤 (기계적 scrollTo 탐지 회피)"""
    try:
        pg.mouse.move(random.randint(250, 900), random.randint(160, 520))
    except Exception:
        pass
    for i in range(rounds):
        try:
            pg.mouse.wheel(0, random.choice([420, 560, 700, 860, 1040, 1280]) + random.randint(-80, 80))
        except Exception:
            pass
        if i % 5 == 0:                      # 내부 스크롤 영역(iframe/모달)도 가끔 훑기
            for fr in pg.frames:
                try:
                    fr.evaluate(SCROLL_JS)
                except Exception:
                    pass
        pg.wait_for_timeout(random.randint(140, 460))
        if random.random() < 0.18:          # 가끔 읽는 척 멈춤
            pg.wait_for_timeout(random.randint(700, 1700))
    try:
        pg.evaluate("window.scrollTo(0,0)")
    except Exception:
        pass
    pg.wait_for_timeout(random.randint(500, 900))


def warm_up(pg, url):
    """상품 URL로 곧바로 직행하지 않고 사이트 첫 화면을 먼저 둘러봄 (자연스러운 동선)"""
    try:
        if "naver.com" in url:
            home = "https://www.naver.com/"
        elif "kakao.com" in url:
            home = "https://store.kakao.com/"
        else:
            return
        pg.goto(home, timeout=30000, wait_until="domcontentloaded")
        pg.wait_for_timeout(random.randint(900, 1800))
        pg.mouse.move(random.randint(300, 900), random.randint(150, 450))
        for _ in range(random.randint(2, 4)):
            pg.mouse.wheel(0, random.randint(180, 520))
            pg.wait_for_timeout(random.randint(200, 520))
    except Exception:
        pass


def looks_blocked(pg):
    """'자동화 의심'류 차단/캡차 화면인지 대략 판별"""
    try:
        t = pg.evaluate("document.body ? document.body.innerText.slice(0,2500) : ''") or ""
    except Exception:
        return False
    if len(t) > 3500:
        return False
    return bool(re.search(r"자동화|비정상적인 접근|접근이 제한|잠시 후 다시|보안\s?확인|captcha|로봇", t, re.I))


STAMP = ROOT / ".lastrun.json"


def pace(url):
    """같은 사이트 연속 요청 간격을 띄워 '기계적 반복' 신호를 줄임"""
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    try:
        d = json.loads(STAMP.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    gap = random.uniform(6, 11)
    if d.get("host") == host:
        wait = gap - (time.time() - float(d.get("ts") or 0))
        if 0 < wait:
            print(f"연속 요청 완화를 위해 {wait:.0f}초 대기…")
            time.sleep(wait)
    try:
        STAMP.write_text(json.dumps({"host": host, "ts": time.time()}), encoding="utf-8")
    except Exception:
        pass


def try_api(pg, url):
    """네이버 스마트스토어/브랜드스토어 내부 API로 상세이미지 확보 (매우 신뢰도 높음)"""
    m = re.search(r"(?:smartstore|brand|m)\.naver\.com/([^/?#]+)/products/(\d+)", url)
    if not m:
        return [], {}, ""
    store, pid = m.group(1), m.group(2)
    apis = [
        f"https://smartstore.naver.com/i/v1/stores/{store}/products/{pid}",
        f"https://brand.naver.com/i/v1/stores/{store}/products/{pid}",
        f"https://smartstore.naver.com/i/v1/stores/{store}/products/{pid}?withWindow=false",
    ]
    for api in apis:
        try:
            r = pg.evaluate(
                "async (u) => { try { const x = await fetch(u, {credentials:'include'});"
                " if(!x.ok) return ''; return await x.text(); } catch(e){ return ''; } }", api)
        except Exception:
            r = ""
        if not r or r.strip()[:1] not in "{[":
            continue
        try:
            d = json.loads(r)
        except Exception:
            continue
        imgs = []

        def push(u):
            c = u and clean(u)
            if c:
                imgs.append(c)
        for k in ("productImages", "images"):
            for x in (d.get(k) or []):
                push(x if isinstance(x, str) else (x.get("url") or x.get("imageUrl")))
        dc = d.get("detailContent") or d.get("detail") or ""
        if dc:
            for mm in re.finditer(r'(https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)[^\s"\'<>]*)', dc):
                push(mm.group(1))
            # 네이버 상세컷은 확장자 없는 shop-phinf URL → 별도 수집
            for mm in re.finditer(r'(https?://shop-phinf\.pstatic\.net/[^\s"\'<>"\']+)', dc):
                push(mm.group(1))
        name = d.get("productName") or d.get("name") or ""
        sp = d.get("salePrice") or d.get("price")
        dp = d.get("discountedPrice") or d.get("discountPrice") or d.get("benefitsView", {}).get("discountedPrice")
        fmt = (lambda v: "" if v in (None, "", 0) else f"{int(v):,}원")
        if imgs or name:
            return imgs, {"t": str(name), "p": fmt(sp), "p2": fmt(dp)}, api
    return [], {}, ""


def main():
    url = sys.argv[1].strip() if len(sys.argv) > 1 else input("상품 URL: ").strip()
    if not url.startswith("http"):
        print("URL이 이상해. http로 시작해야 돼.")
        return

    pace(url)

    from playwright.sync_api import sync_playwright
    print("크롬 여는 중 (사람처럼 열어서 봇차단 우회)…")
    api_meta = {}
    raw = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            channel="chrome",
            headless=False,
            user_agent=UA,
            viewport={"width": 1366, "height": 900},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            ignore_default_args=["--enable-automation"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
            ],
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            print("웹드라이버 흔적:", pg.evaluate("navigator.webdriver"))
        except Exception:
            pass
        warm_up(pg, url)
        pg.goto(url, timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(random.randint(2600, 4600))

        # 차단 화면이면 잠깐 쉬었다가 첫 화면부터 다시 (연속 직행 패턴 완화)
        if looks_blocked(pg):
            print("차단/보안 화면 감지 → 잠시 대기 후 재시도…")
            pg.wait_for_timeout(random.randint(8000, 14000))
            warm_up(pg, url)
            pg.goto(url, timeout=60000, wait_until="domcontentloaded")
            pg.wait_for_timeout(random.randint(3000, 5000))

        # 실제 네이버 로그인 페이지로 튕긴 경우 → 로그인 대기 (전용 프로필에 저장됨)
        login_wait = False
        waited = 0
        while waited < 180 and "nid.naver.com" in pg.url:
            if waited == 0:
                login_wait = True
                print(">>> NAVER_LOGIN_REQUIRED")
                print("네이버가 로그인을 요구해. 지금 열린 크롬 창에서 로그인하면 자동으로 이어져! (최대 3분 대기)")
                try:
                    pg.bring_to_front()
                except Exception:
                    pass
            pg.wait_for_timeout(5000)
            waited += 5
        if waited:
            pg.wait_for_timeout(2000)
        still_login = "nid.naver.com" in pg.url
        if login_wait and still_login:
            print("로그인이 안 돼서 중단됐어. 다시 [배너 자동 생성]을 눌러 로그인 후 사용해줘.")

        print("상세 펼치기 + 끝까지 스크롤 중… (상세컷 lazy로딩 유도)")
        click_more(pg)
        human_scroll(pg, 30)
        raw = collect_all(pg)
        if len(raw) < 4:                     # 부족하면 한 번 더 (일부 사이트는 늦게 로딩)
            click_more(pg)
            human_scroll(pg, 16)
            extra = collect_all(pg)
            _seen = {d.get("u") for d in raw}
            raw += [d for d in extra if d.get("u") not in _seen]

        # 내부 API 보강
        api_imgs, api_meta, api_used = try_api(pg, url)
        if api_imgs:
            print(f"내부 API 적중: 상세이미지 {len(api_imgs)}장 확보")
        raw = [{"u": u, "w": 0, "h": 0, "detail": False} for u in api_imgs] + raw

        meta = {}
        try:
            meta = pg.evaluate("""() => {
              const g=s=>{const m=document.querySelector('meta[property="'+s+'"]')||document.querySelector('meta[name="'+s+'"]');return m?m.content:'';};
              return {title:g('og:title')||document.title||'', site:g('og:site_name'),
                      desc:g('og:description'), brand:g('product:brand')||g('og:brand')};
            }""") or {}
        except Exception:
            meta = {}
        try:
            bt = pg.evaluate("document.body ? document.body.innerText.slice(0,9000) : ''") or ""
        except Exception:
            bt = ""
        ctx.close()

    prices = re.findall(r"\d{1,3}(?:,\d{3})+\s*원", bt)

    dims = {}
    order = []
    for d in raw:
        c = clean(d.get("u") or "")
        if not c:
            continue
        w, h, det = int(d.get("w") or 0), int(d.get("h") or 0), bool(d.get("detail"))
        if c in dims:
            pw, ph, pd = dims[c]
            dims[c] = (max(pw, w), max(ph, h), pd or det)
            continue
        dims[c] = (w, h, det)
        order.append(c)

    def usable(u):
        w, h, det = dims[u]
        if det:
            return True
        if w and h and max(w, h) < 250:   # 작은 아이콘성 썸네일 제외
            return False
        return True

    main = [u for u in order if not dims[u][2] and usable(u)]
    det = [u for u in order if dims[u][2] and usable(u)]
    # 상세컷을 반드시 포함시킨다 (상품 썸네일이 40장을 채워 상세컷이 잘리던 버그 방지)
    imgs = (det + main)[:40]
    dims_out = {u: [dims[u][0], dims[u][1]] for u in imgs}

    brand = (meta.get("brand") or "").strip()
    if not brand:
        m2 = re.search(r"(?:smartstore|brand)\.naver\.com/([^/?#]+)", url)
        if m2:
            brand = m2.group(1)

    data = {
        "url": url,
        "t": (api_meta.get("t") or meta.get("title") or "")[:80],
        "p": api_meta.get("p") or (prices[0] if len(prices) > 0 else ""),
        "p2": api_meta.get("p2") or (prices[1] if len(prices) > 1 else ""),
        "site": (meta.get("site") or brand or "")[:40],
        "brand": brand[:30],
        "desc": (meta.get("desc") or "")[:120],
        "imgs": imgs[:40],
        "dims": dims_out,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"완료! 이미지 {len(imgs)}장 (메인 {len(main)}·상세컷 {len(det)}) → {OUT}")
    print("제목:", data["t"])
    print("가격:", prices[:4])
    print("이제 스튜디오에서 [배너 자동 생성] 누르면 자동 반영돼.")


if __name__ == "__main__":
    main()
