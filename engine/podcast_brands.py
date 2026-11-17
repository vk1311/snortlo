"""Brand looks and fixed hosts for the Keegix Podcast and the Staffkin Podcast.
Colours and fonts come from each brand's 00-BRAND-BIBLE.md in github.com/vk1311/Social-posts."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, "fonts", n)
A = lambda n: os.path.join(HERE, "brand_assets", n)

BRANDS = {
    "keegix": {
        "show": "Keegix Podcast",
        "host": {"name": "Nicole", "role": "Host", "voice": "af_nicole"},
        "guest_voice": "bm_daniel",            # fixed second voice (Vatsal, Nov 11)
        "speed": 1.04,
        "bg": ("#15304A", "#0E2236"),          # harbour navy -> deep navy
        "glows": ("#F4C430", "#E3ECE9", "#2F5C80"),
        "panel": "#FFFFFF", "panel_alt": "#E3ECE9",
        "ink": "#15304A", "muted": "#4E5C66", "accent": "#F4C430", "on_dark": "#FFFFFF", "on_dark_muted": "#B9C7D3",
        "logo": A("logo-lockup-white.png"),
        # (font file, variation axes in file order)
        "head": (F("Newsreader.ttf"), {"Weight": 500, "Optical Size": 48}),
        "head_italic": (F("Newsreader-Italic.ttf"), {"Weight": 500, "Optical Size": 48}),
        "ui_bold": (F("Archivo.ttf"), {"Weight": 800, "Width": 118}),
        "ui": (F("Archivo.ttf"), {"Weight": 500, "Width": 104}),
        "caption": (F("Archivo.ttf"), {"Weight": 600, "Width": 100}),
        "cta": "Free for one property at keegix.com",
        "footer": "AI voices · sources in description",
        "yt_integration": "cmupwpdug0003pj7q6eicvo4q",
        "fb_integration": "cmukftffq002lmk7r1swoip2e",
        "ig_integration": "cmuoai3pj006emk7rf4fvj0lo",
        "hashtags": "#shorttermrental #airbnbhost #bnb",
        "fallback_visuals": ["cottage porch", "bed and breakfast", "guest bedroom"],
    },
    "staffkin": {
        "show": "Staffkin Podcast",
        "host": {"name": "Eric", "role": "Host", "voice": "am_eric"},
        "guest_voice": "am_adam",              # fixed second voice (Vatsal, Nov 11)
        "speed": 1.04,
        "bg": ("#2E2A6B", "#23213F"),          # indigo -> ink
        "glows": ("#7B8CF5", "#EEF0FD", "#4A44A0"),
        "panel": "#F5F6FC", "panel_alt": "#EEF0FD",
        "ink": "#23213F", "muted": "#5F5C85", "accent": "#7B8CF5", "on_dark": "#FFFFFF", "on_dark_muted": "#C3C8F5",
        "logo": A("staffkin-logo-white-1600.png"),
        "head": (F("Outfit.ttf"), {"Weight": 600}),
        "head_italic": (F("Outfit.ttf"), {"Weight": 400}),
        "ui_bold": (F("Outfit.ttf"), {"Weight": 600}),
        "ui": (F("Outfit.ttf"), {"Weight": 400}),
        "caption": (F("Outfit.ttf"), {"Weight": 500}),
        "cta": "Try it free at staffkin.com",
        "footer": "AI voices · sources in description",
        "yt_integration": "cmupwop5v0001pj7qpn3fl617",
        "fb_integration": "cmukfstvx002jmk7r0kumrk2k",
        "ig_integration": "cmuob8g95006imk7r31590lo6",
        "hashtags": "#workplace #burnout #management",
        "fallback_visuals": ["office desk", "empty office", "coffee cup"],
    },
    # Waypoint Software YouTube explainers (approved Nov 12, 2026): ONE narrator, no guest, "chart" palette,
    # Manrope type, chart grid + bearing lines + coordinates, magenta bar, mark bottom-left, waypointns.ca bottom-right.
    "waypoint": {
        "show": "Waypoint Software",
        "solo": True,
        "host": {"name": "Waypoint", "role": "Narrator", "voice": "am_eric"},
        "guest_voice": None,
        "speed": 1.04,
        "bg": ("#1B333F", "#12252F"),          # ink 800 -> chart ink
        "glows": ("#C2185B", "#F2ECE0", "#2F4A56"),
        "panel": "#FBF9F4", "panel_alt": "#F2ECE0",
        "ink": "#12252F", "muted": "#5A6B75", "accent": "#C2185B", "on_dark": "#FFFFFF", "on_dark_muted": "#B8C6CE",
        "logo": A("waypoint-mark-reversed.png"),
        "head": (F("Manrope.ttf"), {"Weight": 800}),
        "head_italic": (F("Manrope.ttf"), {"Weight": 600}),
        "ui_bold": (F("Manrope.ttf"), {"Weight": 800}),
        "ui": (F("Manrope.ttf"), {"Weight": 500}),
        "caption": (F("Manrope.ttf"), {"Weight": 700}),
        "cta": "waypointns.ca",
        "footer": "AI voice · sources in description",
        "coords": "45.08° N  64.50° W",
        "decor": True,
        "outro_len": 5.0,
        "yt_integration": "cmupws29m0005pj7qh21jrsms",
        "hashtags": "#smallbusiness #canada #entrepreneur",
        "fallback_visuals": ["harbour boats", "main street shops", "notebook desk"],
    },
}
