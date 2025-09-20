# scraping_bonpreu.py
# pip install undetected-chromedriver==3.5.5 selenium==4.23.1 pandas

import argparse
import random
import re
import sys
import time
from datetime import datetime
from urllib.parse import unquote, urlparsefPA

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as W

BASE = "https://www.compraonline.bonpreuesclat.cat"


# ---------- CLI ----------
def build_parser():
    p = argparse.ArgumentParser(
        description="Scraper de listados de productos Bonpreu/Esclat."
    )
    p.add_argument(
        "url",
        help="URL de la categoría (pega aquí la URL con %XX o acentos, da igual).",
    )
    p.add_argument(
        "-o",
        "--out",
        help="Ruta del CSV de salida. Si no se indica, se genera automáticamente.",
    )
    p.add_argument(
        "--headless", action="store_true", help="Ejecutar Chrome en modo headless."
    )
    p.add_argument(
        "--max-loops",
        type=int,
        default=400,  # ↓ antes 240/1500 en llamada
        help="Máximo de ciclos de micro-scroll (por defecto: 400).",
    )
    p.add_argument(
        "--step",
        type=int,
        default=100,  # ↓ paso más fino por defecto
        help="Paso de scroll en píxeles (por defecto: 100).",
    )
    p.add_argument(
        "--passes",
        type=int,
        default=0,  # ↓ evita saltos largos iniciales
        help="Scrolls rápidos iniciales (por defecto: 0).",
    )
    return p


def safe_slug_from_url(url: str) -> str:
    """
    Intenta crear un nombre legible para el CSV a partir de la URL de la categoría.
    """
    path = unquote(urlparse(url).path)  # decodifica %XX
    # Tomamos el último segmento "no-uuid" como etiqueta (p.ej. 'arròs' o 'pasta-seca')
    parts = [x for x in path.split("/") if x]
    label = ""
    for seg in reversed(parts):
        # ignora posibles UUIDs
        if not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", seg, re.I
        ):
            label = seg
            break
    if not label:
        label = parts[-1] if parts else "categoria"
    # normaliza a slug sencillo
    label = re.sub(r"\s+", "-", label.lower())
    label = re.sub(r"[^a-z0-9\-]+", "-", label)  # quita acentos/símbolos
    label = re.sub(r"-+", "-", label).strip("-")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"bonpreu_{label}_{ts}.csv"


# ---------- DRIVER ----------
def setup_driver(headless=False):
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=ca-ES,ca;q=0.9,es-ES;q=0.8")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    )
    d = uc.Chrome(options=opts)
    try:
        d.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            },
        )
    except Exception:
        pass
    return d


# ---------- COOKIES ----------
def accept_cookies(d, timeout=15):
    w = W(d, timeout)
    xpaths = [
        '//*[@id="onetrust-accept-btn-handler"]',
        '//*[@data-testid="uc-accept-all-button"]',
        '//button[contains(.,"Acceptar-ho tot")]',
        '//button[contains(.,"Acceptar")]',
        '//button[contains(.,"Accept all")]',
    ]
    for xp in xpaths:
        try:
            w.until(EC.element_to_be_clickable((By.XPATH, xp))).click()
            time.sleep(1)
            print("✅ Cookies aceptadas.")
            return
        except Exception:
            pass
    # iframes
    try:
        ifs = d.find_elements(
            By.CSS_SELECTOR,
            'iframe[src*="consent"],iframe[id*="consent"],iframe[src*="cmp"],iframe[id*="ot-"],iframe[src*="didomi"]',
        )
        for fr in ifs:
            d.switch_to.frame(fr)
            for xp in xpaths:
                try:
                    btn = d.find_element(By.XPATH, xp)
                    btn.click()
                    time.sleep(1)
                    d.switch_to.default_content()
                    print("✅ Cookies aceptadas (iframe).")
                    return
                except Exception:
                    pass
            d.switch_to.default_content()
    except Exception:
        d.switch_to.default_content()
    print("ℹ️ Sin banner de cookies (seguimos).")


# ---------- HELPERS ----------
def get_base_url(d):
    return d.execute_script("return location.origin;")


def wait_skeletons_settle(d, timeout=8.0, poll=0.25):
    t0 = time.time()
    last = -1
    stable = 0
    while time.time() - t0 < timeout:
        sk = len(d.find_elements(By.CSS_SELECTOR, '[data-test="fop-skeleton"]'))
        if sk == 0:
            return
        if sk == last:
            stable += 1
        else:
            stable = 0
            last = sk
        if stable >= 3:
            return
        time.sleep(poll)


def parse_cards_in_dom(d, BASE):
    js = r"""
      const BASE = arguments[0];
      const cards = Array.from(document.querySelectorAll('[data-retailer-anchor="fop"]'));
      const norm = s => s ? s.trim().replace(/\u00A0/g,' ') : null;
      return cards.map(c=>{
        const A = c.querySelector('a[data-test="fop-product-link"][aria-hidden="false"]')
              || c.querySelector('a[data-test="fop-product-link"]');
        const hrefRaw = A ? A.getAttribute('href') : null;
        const link = hrefRaw ? new URL(hrefRaw, BASE).href : null;  // ✅ absoluta + encoded
        const t = c.querySelector('[data-test="fop-title"]');
        const price = c.querySelector('[data-test="fop-price"], [data-test="fop-price-now"], [data-test="fop-price-current"]');
        const ppu = c.querySelector('[data-test="fop-price-per-unit"]');
        const size = c.querySelector('[data-test="fop-size"]');
        return {
          name: norm(t && t.textContent),
          price: norm(price && price.textContent),
          price_per_unit: norm(ppu && ppu.textContent),
          size: norm(size && size.textContent),
          href: link
        };
      }).filter(x => x.name || x.price);
    """
    try:
        return d.execute_script(js, BASE) or []
    except Exception:
        return []


def micro_scroll(d, container, step=180):
    d.execute_script("arguments[0].scrollBy(0, arguments[1]);", container, step)
    d.execute_script("arguments[0].scrollBy(0, -40);", container)


def scroll_products(d, passes=3):
    grid = None
    try:
        grid = d.find_element(By.CSS_SELECTOR, '[data-retailer-anchor="product-list"]')
    except Exception:
        pass
    last = 0
    for i in range(1, passes + 1):
        if grid:
            d.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", grid
            )
        d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.0, 1.6))
        d.execute_script("window.scrollBy(0, -200);")
        time.sleep(random.uniform(0.2, 0.5))
        n = len(d.find_elements(By.CSS_SELECTOR, '[data-retailer-anchor="fop"]'))
        print(f"🧮 Scroll {i}: {n} productos visibles")
        if n == last:
            break
        last = n


def robust_scroll_and_collect(
    d,
    step_px=140,
    idle_wait=(0.35, 0.55),
    max_total_loops=1200,
    no_growth_rounds=6,
    bottom_passes=3,
):
    """
    Scroller robusto para listas virtualizadas.
    - step_px: paso pequeño para disparar observers
    - idle_wait: espera aleatoria entre pasos
    - max_total_loops: tope duro de seguridad
    - no_growth_rounds: cuántas rondas seguidas sin crecer para cortar
    - bottom_passes: nº de “barridos de fondo” para forzar la última carga
    """
    BASE = get_base_url(d)
    collected = {}
    last_unique = 0
    rounds_no_growth = 0
    touched_bottom = 0

    # --- ventana de crecimiento para "meseta"
    growth_window = 20
    uniques_history = []

    # Detecta contenedor scrolleable
    try:
        grid = d.find_element(By.CSS_SELECTOR, '[data-retailer-anchor="product-list"]')
    except Exception:
        grid = None

    def scroll_top():
        if grid:
            d.execute_script("arguments[0].scrollTo(0,0);", grid)
        else:
            d.execute_script("window.scrollTo(0,0);")

    def scroll_by(px):
        if grid:
            d.execute_script("arguments[0].scrollBy(0, arguments[1]);", grid, px)
            d.execute_script("arguments[0].scrollBy(0, -40);", grid)  # rebote
        else:
            d.execute_script("window.scrollBy(0, arguments[0]);", px)
            d.execute_script("window.scrollBy(0, -40);")

    def at_bottom():
        if grid:
            return d.execute_script(
                "return Math.ceil(arguments[0].scrollTop + arguments[0].clientHeight) >= arguments[0].scrollHeight;",
                grid,
            )
        return d.execute_script(
            "return Math.ceil(window.scrollY + window.innerHeight) >= document.body.scrollHeight;"
        )

    # Arranca en el top y captura inicial
    scroll_top()
    time.sleep(0.8)
    wait_skeletons_settle(d)

    snap = parse_cards_in_dom(d, BASE)
    for r in snap:
        key = r["href"] or f"{r.get('name', '')}|{r.get('size', '')}"
        if key and key not in collected:
            collected[key] = r
    print(f"📸 Inicial: viewport={len(snap)} | únicos={len(collected)}")

    # Bucle principal
    for i in range(1, max_total_loops + 1):
        # --- step adaptativo (fino si no crece o estamos al fondo)
        # evaluamos "al fondo" antes de movernos
        at_bottom_flag = at_bottom()
        effective_step = step_px
        if rounds_no_growth >= 2:
            effective_step = max(60, int(step_px * 0.7))  # afina si no crece
        if at_bottom_flag:
            effective_step = max(50, int(effective_step * 0.6))  # ultra-fino al fondo

        # Paso corto
        scroll_by(effective_step)
        time.sleep(random.uniform(*idle_wait))
        wait_skeletons_settle(d)

        # “Asegura” que la última card visible entra al viewport (dispara observers)
        d.execute_script("""
          const cards = document.querySelectorAll('[data-retailer-anchor="fop"]');
          if (cards.length) { cards[cards.length-1].scrollIntoView({block:'center'}); }
        """)

        # Captura
        snap = parse_cards_in_dom(d, BASE)
        for r in snap:
            key = r["href"] or f"{r.get('name', '')}|{r.get('size', '')}"
            if key and key not in collected:
                collected[key] = r

        uniques = len(collected)
        print(f"🐢 Loop {i}: únicos={uniques} (viewport={len(snap)})")

        # Gestión de crecimiento
        if uniques == last_unique:
            rounds_no_growth += 1
        else:
            rounds_no_growth = 0
        last_unique = uniques

        # Historial de crecimiento reciente (para meseta)
        uniques_history.append(uniques)
        if len(uniques_history) > growth_window:
            uniques_history.pop(0)
        recent_growth = (
            (uniques - uniques_history[0])
            if len(uniques_history) == growth_window
            else 999
        )

        # ¿Estamos en el fondo?
        if at_bottom_flag:
            touched_bottom += 1
            # En el fondo hacemos pequeños “peines” para forzar la última carga
            for _ in range(2):
                scroll_by(80)
                time.sleep(random.uniform(*idle_wait))
                wait_skeletons_settle(d)
            # Una micro-subida y re-entrada
            if grid:
                d.execute_script("arguments[0].scrollBy(0, -120);", grid)
            else:
                d.execute_script("window.scrollBy(0, -120);")
            time.sleep(random.uniform(*idle_wait))
            wait_skeletons_settle(d)

        # Corte por meseta: si ya tocamos fondo y no hay crecimiento significativo
        if touched_bottom >= 2 and rounds_no_growth >= 2 and recent_growth <= 1:
            print("🛑 Corte por meseta (sin crecimiento reciente).")
            break

        # Criterio de salida clásico: varias rondas sin crecer y ya tocamos fondo X veces
        if rounds_no_growth >= no_growth_rounds and touched_bottom >= bottom_passes:
            break

    # Barridos finales obligados en el fondo
    for _ in range(bottom_passes):
        if grid:
            d.execute_script(
                "arguments[0].scrollTo(0, arguments[0].scrollHeight);", grid
            )
        else:
            d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(0.6, 0.9))
        wait_skeletons_settle(d)
        snap = parse_cards_in_dom(d, BASE)
        for r in snap:
            key = r["href"] or f"{r.get('name', '')}|{r.get('size', '')}"
            if key and key not in collected:
                collected[key] = r

    # Auditoría rápida (qué hay en DOM ahora y no en nuestra lista)
    dom_now = (
        d.execute_script("""
          const BASE = location.origin;
          return Array.from(
            document.querySelectorAll('[data-retailer-anchor="fop"], [data-test^="fop-wrapper:"]')
          ).map(c=>{
            const a = c.querySelector('a[data-test="fop-product-link"][aria-hidden="false"]')
                    || c.querySelector('a[data-test="fop-product-link"]');
            if(!a) return null;
            const hrefRaw = a.getAttribute('href');
            return hrefRaw ? new URL(hrefRaw, BASE).href : null;
          }).filter(Boolean);
        """)
        or []
    )

    got = {r["href"] for r in collected.values() if r.get("href")}
    missing = [u for u in dom_now if u not in got]
    print(
        f"🧪 DOM total={len(dom_now)} | recolectados(con href)={len(got)} | faltan(en DOM actual)={len(missing)}"
    )
    for u in missing[:5]:
        print("   • falta:", u)

    return list(collected.values())


# ---------- MAIN ----------
def main():
    parser = build_parser()
    args = parser.parse_args()

    # Validación básica del dominio
    if "compraonline.bonpreuesclat.cat" not in urlparse(args.url).netloc:
        print("❌ La URL debe ser de compraonline.bonpreuesclat.cat", file=sys.stderr)
        sys.exit(2)

    OUT = args.out or safe_slug_from_url(args.url)

    d = setup_driver(headless=args.headless)
    try:
        d.get(args.url)
        time.sleep(3)
        accept_cookies(d)

        # Esperar a que haya al menos 1 card
        try:
            W(d, 25).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-retailer-anchor="fop"]')
                )
            )
        except Exception:
            time.sleep(2)

        # Scrolls rápidos opcionales
        scroll_products(d, passes=args.passes)

        rows = robust_scroll_and_collect(
            d,
            step_px=args.step,
            idle_wait=(0.35, 0.55),
            max_total_loops=args.max_loops,
            no_growth_rounds=3,  # ↓ corta antes si no crece
            bottom_passes=3,  # peina el fondo 3 veces
        )

        pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
        print(f"✅ {len(rows)} productos guardados en {OUT}")
    finally:
        d.quit()


if __name__ == "__main__":
    main()
