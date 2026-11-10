#!/usr/bin/env python3
import base64, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
TPL = pathlib.Path(__file__).with_name("template.html")
OUT = ROOT / "docs/design/design-system.html"
LOGO = ROOT / "apps/frontend/public/logo"


def data_uri(path):
    raw = pathlib.Path(path).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()


def img(name, cls="", style="", alt="Spendy"):
    uri = data_uri(LOGO / name)
    parts = [f'<img src="{uri}" alt="{alt}"']
    if cls:
        parts.append(f'class="{cls}"')
    if style:
        parts.append(f'style="{style}"')
    return " ".join(parts) + ">"


def svg_ill(inner: str) -> str:
    return (
        '<svg viewBox="0 0 160 150" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + inner
        + '</svg>'
    )


ICONS = {
    "IC_GRID": '<path d="M4 3h5a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1ZM15 3h5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1ZM15 12h5a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1ZM4 16h5a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1Z"/>',
    "IC_SWAP": '<path d="M13 16H8M14 8H8M16 12H8M4 3a1 1 0 0 1 1-1 1.3 1.3 0 0 1 .7.2l.933.6a1.3 1.3 0 0 0 1.4 0l.934-.6a1.3 1.3 0 0 1 1.4 0l.933.6a1.3 1.3 0 0 0 1.4 0l.933-.6a1.3 1.3 0 0 1 1.4 0l.934.6a1.3 1.3 0 0 0 1.4 0l.933-.6A1.3 1.3 0 0 1 19 2a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1 1.3 1.3 0 0 1-.7-.2l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.934.6a1.3 1.3 0 0 1-1.4 0l-.933-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-1.4 0l-.934-.6a1.3 1.3 0 0 0-1.4 0l-.933.6a1.3 1.3 0 0 1-.7.2 1 1 0 0 1-1-1z"/>',
    "IC_CARD": '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    "IC_PIG": '<path d="M11 17h3v2a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-3a3.16 3.16 0 0 0 2-2h1a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1h-1a5 5 0 0 0-2-4V3a4 4 0 0 0-3.2 1.6l-.3.4H11a6 6 0 0 0-6 6v1a5 5 0 0 0 2 4v3a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1zM16 10h.01M2 8v1a2 2 0 0 0 2 2h1"/>',
    "IC_REPEAT": '<path d="M2 12a10 10 0 1 0 20 0a10 10 0 1 0-20 0M12 6v6l4 2"/>',
    "IC_TREND": '<path d="M16 7h6v6M22 7l-8.5 8.5-5-5L2 17"/>',
    "IC_TRASH": '<path d="M10 11v6M14 11v6M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "IC_SLIDERS": '<path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915M9 12a3 3 0 1 0 6 0a3 3 0 1 0-6 0"/>',
    "IC_PLUS": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "IC_ALERT": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "IC_CHECK": '<path d="M20 6 9 17l-5-5"/>',
    "IC_FOCUS": '<path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/>',
    "IC_KEY": '<rect x="2" y="6" width="20" height="12" rx="2.4"/><path d="M6 10h.01"/><path d="M10 10h.01"/><path d="M14 10h.01"/><path d="M18 10h.01"/><path d="M8 14h8"/>',
    "IC_TOUCH": '<circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="2.6"/>',
    "IC_CHART": '<path d="M3 3v18h18"/><path d="m7 15 4-5 3 3 5-7"/>',
    "IC_MOON": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
    "IC_SUN": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "IC_MONITOR": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "IC_TAG": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42zM7 7.5a0.5 0.5 0 1 0 1 0a0.5 0.5 0 1 0-1 0"/>',
    "IC_USER": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M8 7a4 4 0 1 0 8 0a4 4 0 1 0-8 0"/>',
    "IC_ARROW_DL": '<path d="M17 7 7 17M17 17H7V7"/>',
    "IC_ARROW_UR": '<path d="M7 17 17 7M7 7h10v10"/>',
    "IC_MOTION": '<path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z"/>',
    "IC_MORE": '<path d="M11 12a1 1 0 1 0 2 0a1 1 0 1 0-2 0M18 12a1 1 0 1 0 2 0a1 1 0 1 0-2 0M4 12a1 1 0 1 0 2 0a1 1 0 1 0-2 0"/>',
    "IC_ARROW_R": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
}


def icon(key, size=16):
    return (
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICONS[key]}</svg>'
    )


ILL = """<svg viewBox="0 0 170 152" fill="none" stroke="currentColor" stroke-width="2"
 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M44 24h72v102l-9-6-9 6-9-6-9 6-9-6-9 6-9-6-9 6V24Z"/>
  <path d="M58 44h44M58 58h44M58 72h28"/>
  <path d="M58 88h20"/>
  <circle cx="128" cy="106" r="17"/>
  <path d="M133 99a9 9 0 1 0 0 14"/>
  <path d="M119 104h10M119 110h10"/>
</svg>"""

REPL = {
    "F400": None, "F500": None, "F600": None, "F700": None,
    "LOCKUP_H_DARK": img("spendy-lockup-h-black-on-dark.svg", "lockup"),
    "LOCKUP_H_DARKBIG": img("spendy-lockup-h-black-on-dark.svg", "lock-big"),
    "LOCKUP_H_LIGHT": img("spendy-lockup-h-black-on-light.svg", "lock-big", "width:min(100%,320px)"),
    "LOCKUP_V_DARK": img("spendy-lockup-v-black-on-dark.svg", "lock-vert"),
    "SYM64": img("spendy-symbol.svg", "", "width:64px;height:64px"),
    "SYM32": img("spendy-symbol.svg", "", "width:32px;height:32px"),
    "SYM16": img("spendy-symbol.svg", "", "width:16px;height:16px"),
    "SYM_MONO_WHITE": img("spendy-symbol-mono-white.svg", "", "height:30px"),
    "SYM_MONO_BLACK": img("spendy-symbol-mono-black.svg", "", "height:30px"),
    "LOCKUP_H_DARKSMALL": img("spendy-lockup-h-black-on-dark.svg", "mini-brand"),
    "LOCKUP_H_LIGHTSMALL": img("spendy-lockup-h-black-on-light.svg", "mini-brand"),
    "LOCKUP_H_DARKSMALLWF": img("spendy-lockup-h-black-on-dark.svg", "brand"),
    "ILL_ACCOUNTS": svg_ill("""<rect x="30" y="56" width="100" height="64" rx="14"/><path d="M30 76h100"/><circle cx="108" cy="96" r="6"/><circle cx="112" cy="40" r="11"/><circle cx="112" cy="40" r="4"/>"""),
    "ILL_MOVEMENTS": svg_ill("""<path d="M46 20h50l22 22v88H46z"/><path d="M96 20v22h22"/><circle cx="82" cy="76" r="18"/><path d="M90 67a12 12 0 1 0 0 18"/><path d="M72 72h15M72 80h15"/><path d="M60 112h34"/><path d="M87 105l7 7-7 7"/>"""),
    "ILL_SAVINGS": svg_ill("""<rect x="30" y="60" width="96" height="52" rx="26"/><path d="M94 66l8-18 14 14"/><path d="M126 74h10a9 9 0 0 1 0 18h-10"/><path d="M52 112v14M82 112v14M112 112v14"/><path d="M62 70h20"/><path d="M30 82c-9-3-12 9-3 12"/><circle cx="72" cy="44" r="9"/>"""),
    "ILL_INVESTMENTS": svg_ill("""<path d="M30 34v78h104"/><rect x="48" y="84" width="18" height="28" rx="3"/><rect x="78" y="64" width="18" height="48" rx="3"/><rect x="108" y="44" width="18" height="68" rx="3"/>"""),
    "ILL_AUTOMATIONS": svg_ill("""<circle cx="76" cy="80" r="30"/><path d="M76 80V62M76 80h14"/><path d="M112 64a40 40 0 0 1 0 32"/><path d="M105 89l7 7 7-7"/>"""),
    "ILL_TRASH": svg_ill("""<path d="M44 46h72"/><path d="M68 46v-8a6 6 0 0 1 6-6h12a6 6 0 0 1 6 6v8"/><path d="M50 46l6 74a8 8 0 0 0 8 7h32a8 8 0 0 0 8-7l6-74"/><path d="M68 66v40M80 66v40M92 66v40"/>"""),
    "SYM_FAVICON": '<span style="display:inline-flex;align-items:center;justify-content:center;'
                   'width:44px;height:44px;border-radius:12px;background:#0b0f0d;'
                   'border:1px solid #26302b">' + img("spendy-symbol.svg", "", "height:26px") + '</span>',
}

fonts = {
    400: "Inter-Regular.ttf",
    500: "Inter-Medium.ttf",
    600: "Inter-SemiBold.ttf",
    700: "Inter-Bold.ttf",
}
for w, f in fonts.items():
    REPL[f"F{w}"] = base64.b64encode(
        (ROOT / "apps/frontend/public/fonts" / f).read_bytes()).decode()

for key in ICONS:
    REPL[key] = icon(key)

html = TPL.read_text()
for k, v in REPL.items():
    token = f"@@{k}@@"
    if token not in html:
        print("UNUSED placeholder:", k)
    html = html.replace(token, v)

left = [l for l in html.split("@@") if l and len(l) < 40]
print("residui:", left[:10])
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html)
print("scritto", OUT, f"{OUT.stat().st_size/1024:.0f} KB")
