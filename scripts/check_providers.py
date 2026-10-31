"""Test every configured external service and print exactly what it says.

The app deliberately degrades quietly when a provider fails — a dead upstream
must never take the site down. The cost of that is a generic message in the UI,
so this script exists to get the real answer:

    .venv/bin/python -m scripts.check_providers
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402

from app.core.config import settings  # noqa: E402

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}OK{RESET}   {msg}")


def bad(msg: str) -> None:
    print(f"  {RED}FAIL{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}WARN{RESET} {msg}")


def mask(value: str | None) -> str:
    if not value:
        return "(not set)"
    return f"{value[:4]}…{value[-3:]} ({len(value)} chars)"


def check_internet() -> bool:
    """Probe endpoints built for reachability checks.

    An earlier version used api.github.com, which rate-limits unauthenticated
    callers and so reported FAIL on a working connection — a check that cries
    wolf is worse than no check.
    """
    print("\nInternet")
    for url in ("https://connectivitycheck.gstatic.com/generate_204",
                "https://cloudflare.com/cdn-cgi/trace",
                "https://example.com"):
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            if r.status_code < 400:
                ok(f"this machine can reach the internet ({url.split('/')[2]})")
                return True
        except Exception:
            continue
    bad("could not reach any test endpoint — check your connection, VPN or proxy")
    return False


def check_waqi() -> None:
    print(f"\nWAQI / AQICN  key={mask(settings.waqi_token)}")
    if not settings.waqi_token:
        warn("no WAQI_TOKEN in .env — live air quality is disabled")
        return
    try:
        r = httpx.get("https://api.waqi.info/feed/mumbai/",
                      params={"token": settings.waqi_token}, timeout=15)
        print(f"  {DIM}HTTP {r.status_code}{RESET}")
        body = r.json()
        status = body.get("status")
        if status == "ok":
            data = body["data"]
            observed = data["time"]["s"]
            ok(f"live AQI for {data['city']['name']}: {data['aqi']} "
               f"at {observed}")
            # A feed can answer 200 and still be long dead. AIRS refuses to
            # present a stale observation as "now", so surface the age here.
            try:
                from datetime import datetime, timezone
                ts = datetime.fromisoformat(observed.replace(" ", "T"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if hours > 6:
                    warn(f"but that reading is {hours:,.0f} h old — this station's "
                         "feed is stale, so AIRS will fall back to stored data "
                         "and say so in the banner")
                else:
                    ok(f"reading is {hours:.1f} h old — fresh enough to use")
            except Exception:
                pass
        else:
            # WAQI puts the real reason in `data` when status is not ok, e.g.
            # "Invalid key" or "Over quota".
            bad(f"WAQI refused the request: status={status!r} data={body.get('data')!r}")
    except Exception as exc:
        bad(f"{type(exc).__name__}: {exc}")


def check_waqi_network() -> None:
    print("\nWAQI station network (what AIRS now uses for city averages)")
    if not settings.waqi_token:
        return
    try:
        from app.services.providers.waqi import WaqiProvider
        stations = WaqiProvider().india_index()
        fresh = [s for s in stations if s.aqi is not None
                 and (s.age_hours() or 99) <= 3]
        ok(f"{len(stations)} Indian stations listed, {len(fresh)} reported in "
           "the last 3 hours")
    except Exception as exc:
        bad(f"could not load the station list: {type(exc).__name__}: "
            f"{getattr(exc, 'detail', None) or exc}")


def check_open_meteo() -> None:
    print("\nOpen-Meteo (CAMS model: history, forecast, weather — no key needed)")
    try:
        from app.services.providers import openmeteo
        obs = openmeteo.OpenMeteoAirProvider().fetch(28.6139, 77.2090)
        ok(f"modelled US AQI for Delhi right now: {obs.aqi}")
        wx = openmeteo.OpenMeteoWeatherProvider().fetch(19.076, 72.8777)
        ok(f"weather for Mumbai: {wx.temperature_c}°C, {wx.condition}")
    except Exception as exc:
        bad(f"{type(exc).__name__}: {getattr(exc, 'detail', None) or exc}")


def check_openweather() -> None:
    print(f"\nOpenWeatherMap  key={mask(settings.openweather_api_key)}")
    if not settings.openweather_api_key:
        warn("no OPENWEATHER_API_KEY in .env — live weather is disabled")
        return
    try:
        r = httpx.get("https://api.openweathermap.org/data/2.5/weather",
                      params={"lat": 19.076, "lon": 72.8777, "units": "metric",
                              "appid": settings.openweather_api_key}, timeout=15)
        print(f"  {DIM}HTTP {r.status_code}{RESET}")
        if r.status_code == 200:
            main = r.json()["main"]
            ok(f"live weather: {main['temp']}°C, {main['humidity']}% humidity")
        elif r.status_code == 401:
            bad("key rejected (HTTP 401). A new OpenWeather key can take up to "
                "2 hours to activate. Message: "
                f"{r.json().get('message')}")
        else:
            bad(f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        bad(f"{type(exc).__name__}: {exc}")


def check_gemini() -> None:
    print(f"\nGemini  key={mask(settings.gemini_api_key)}  "
          f"model={settings.gemini_model}")
    if not settings.gemini_api_key:
        warn("no GEMINI_API_KEY in .env — the assistant is disabled")
        return

    # Ask the API which models this key can actually use. This separates the
    # three failure modes that all look identical from the UI: a bad key, a
    # model name this key cannot access, and a network problem.
    try:
        r = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": settings.gemini_api_key}, timeout=20)
        print(f"  {DIM}HTTP {r.status_code} on model list{RESET}")
        if r.status_code != 200:
            detail = r.json().get("error", {}) if r.text.startswith("{") else {}
            bad(f"key rejected: {detail.get('status', r.status_code)} — "
                f"{detail.get('message', r.text[:200])}")
            return
        names = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        ok(f"key valid — {len(names)} usable models")
        wanted = settings.gemini_model
        if wanted in names:
            ok(f"configured model {wanted!r} is available")
        else:
            warn(f"configured model {wanted!r} is NOT available to this key")
            flash = [n for n in names if "flash" in n and "thinking" not in n]
            print(f"  {DIM}available flash models: {', '.join(flash[:8])}{RESET}")
            if flash:
                print(f"  {YELLOW}→ set GEMINI_MODEL={flash[0]} in .env "
                      f"(AIRS also falls back automatically){RESET}")
            # Do not stop here: the app falls back to other models, and whether
            # that fallback actually reaches one is the useful answer.
    except Exception as exc:
        bad(f"could not reach the Gemini API: {type(exc).__name__}: {exc}")
        return

    # An out-of-date client is its own failure mode: 0.8.0 predates every
    # model a current key can use.
    try:
        import google.genai as _genai
        version = getattr(_genai, "__version__", "unknown")
        major = int(str(version).split(".")[0]) if str(version)[:1].isdigit() else 0
        if major >= 2:
            ok(f"google-genai SDK {version}")
        else:
            bad(f"google-genai SDK is {version} — too old for current models")
            print(f"  {YELLOW}→ .venv/bin/pip install -U google-genai{RESET}")
    except Exception:
        warn("could not determine the google-genai version")

    _gemini_app_path()


def _gemini_app_path() -> None:
    # Now the real thing, through the same client library the app uses.
    try:
        from app.ai import gemini
        answer = gemini.generate(
            "You are a test harness. Reply with exactly: AIRS_OK",
            "Reply now.", temperature=0.0, max_output_tokens=20)
        ok(f"the app's own AI path works — model replied {answer.strip()!r}")
    except Exception as exc:
        bad(f"the app's AI path failed: {type(exc).__name__}: {exc}")
        cause = exc.__cause__
        while cause is not None:
            print(f"  {DIM}caused by {type(cause).__name__}: {cause}{RESET}")
            cause = cause.__cause__


if __name__ == "__main__":
    print("=" * 68)
    print("AIRS provider check")
    print(f"  data mode: {settings.airs_data_mode}")
    print("=" * 68)
    check_internet()
    check_waqi()
    check_waqi_network()
    check_open_meteo()
    check_openweather()
    check_gemini()
    print("\nDone. Anything marked FAIL above is why that feature is quiet.\n")
