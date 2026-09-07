"""Reference data: cities, monitoring stations and the intervention catalogue.

These are *reference* rows, not measurements — they are safe to load in both
live and demo mode. Station coordinates and zone characteristics follow the
real CPCB/SAFAR network layout in each city so that the map and the source
attribution logic behave plausibly.
"""
from __future__ import annotations

CITIES = [
    {
        "slug": "delhi", "name": "Delhi NCR", "country": "India",
        "latitude": 28.6139, "longitude": 77.2090, "population": 32_900_000,
        "default_zoom": 11, "waqi_keyword": "delhi", "aqi_scale": "us_epa",
        "stations": [
            ("DL-ANV", "Anand Vihar", 28.6469, 77.3161, "traffic_corridor", 480_000, True, True, False),
            ("DL-ITO", "ITO Junction", 28.6289, 77.2410, "traffic_corridor", 350_000, True, False, True),
            ("DL-RKP", "R K Puram", 28.5636, 77.1866, "residential", 290_000, False, False, False),
            ("DL-PBG", "Punjabi Bagh", 28.6742, 77.1310, "mixed", 310_000, True, False, True),
            ("DL-DWK", "Dwarka Sector 8", 28.5710, 77.0710, "residential", 260_000, False, False, True),
            ("DL-MDK", "Mundka", 28.6824, 77.0326, "industrial", 180_000, True, True, False),
            ("DL-JHP", "Jahangirpuri", 28.7328, 77.1707, "industrial", 340_000, True, True, False),
            ("DL-ROH", "Rohini Sector 16", 28.7325, 77.1199, "residential", 300_000, False, False, True),
            ("DL-NJF", "Najafgarh", 28.6090, 76.9855, "mixed", 150_000, False, False, False),
            ("DL-LOD", "Lodhi Road", 28.5918, 77.2273, "green", 120_000, False, False, False),
        ],
    },
    {
        "slug": "mumbai", "name": "Mumbai", "country": "India",
        "latitude": 19.0760, "longitude": 72.8777, "population": 21_300_000,
        "default_zoom": 11, "waqi_keyword": "mumbai", "aqi_scale": "us_epa",
        "stations": [
            ("MU-BKC", "Bandra Kurla Complex", 19.0607, 72.8686, "commercial", 320_000, True, False, True),
            ("MU-COL", "Colaba", 18.9067, 72.8147, "mixed", 180_000, False, False, False),
            ("MU-WOR", "Worli", 19.0176, 72.8156, "residential", 240_000, True, False, True),
            ("MU-POW", "Powai", 19.1176, 72.9060, "residential", 200_000, False, False, True),
            ("MU-CHE", "Chembur", 19.0522, 72.9005, "industrial", 350_000, True, True, False),
            ("MU-MAL", "Malad West", 19.1860, 72.8489, "mixed", 290_000, True, False, True),
            ("MU-BOR", "Borivali East", 19.2290, 72.8567, "residential", 260_000, False, False, False),
            ("MU-MZG", "Mazgaon", 18.9646, 72.8425, "industrial", 210_000, True, True, False),
        ],
    },
    {
        "slug": "pune", "name": "Pune", "country": "India",
        "latitude": 18.5204, "longitude": 73.8567, "population": 7_400_000,
        "default_zoom": 11, "waqi_keyword": "pune", "aqi_scale": "us_epa",
        "stations": [
            ("PN-SVN", "Shivajinagar", 18.5308, 73.8475, "commercial", 210_000, True, False, True),
            ("PN-KRV", "Karve Road", 18.5018, 73.8206, "traffic_corridor", 180_000, True, False, False),
            ("PN-HDP", "Hadapsar", 18.5089, 73.9260, "industrial", 240_000, True, True, True),
            ("PN-KTJ", "Katraj", 18.4487, 73.8560, "residential", 160_000, False, False, False),
            ("PN-BHS", "Bhosari", 18.6298, 73.8478, "industrial", 190_000, True, True, False),
            ("PN-PMP", "Pimpri", 18.6279, 73.8009, "mixed", 220_000, True, True, True),
        ],
    },
    {
        "slug": "bengaluru", "name": "Bengaluru", "country": "India",
        "latitude": 12.9716, "longitude": 77.5946, "population": 13_600_000,
        "default_zoom": 11, "waqi_keyword": "bangalore", "aqi_scale": "us_epa",
        "stations": [
            ("BL-HBL", "Hebbal", 13.0358, 77.5970, "traffic_corridor", 280_000, True, False, True),
            ("BL-SLK", "Silk Board", 12.9172, 77.6229, "traffic_corridor", 330_000, True, False, True),
            ("BL-BTM", "BTM Layout", 12.9166, 77.6101, "residential", 250_000, False, False, False),
            ("BL-PNY", "Peenya", 13.0287, 77.5195, "industrial", 300_000, True, True, False),
            ("BL-JYN", "Jayanagar", 12.9250, 77.5938, "residential", 210_000, False, False, False),
            ("BL-CRS", "City Railway Station", 12.9784, 77.5713, "commercial", 190_000, True, False, True),
        ],
    },
]



# ── The rest of the Indian network ────────────────────────────────────
# The four metros above carry a full multi-station network. Every other city
# gets one representative city-centre receptor: enough for the national map,
# the city comparison and the forecast, without turning a demo backfill into
# half a million rows. Adding more stations to any city is just more tuples.
#
# (slug, display name, lat, lon, annual-mean PM2.5 baseline in ug/m3, zone)
# Baselines follow the broad pattern of CPCB annual averages — the Indo-Gangetic
# plain far worse than the coasts and the south — so the national map is
# plausible rather than uniform.

MORE_CITIES: list[tuple[str, str, float, float, float, str]] = [
    # ── Indo-Gangetic plain: the worst air in the country ──
    ("kanpur",        "Kanpur",              26.4499, 80.3319, 88.0, "industrial"),
    ("lucknow",       "Lucknow",             26.8467, 80.9462, 82.0, "mixed"),
    ("agra",          "Agra",                27.1767, 78.0081, 78.0, "mixed"),
    ("varanasi",      "Varanasi",            25.3176, 82.9739, 80.0, "mixed"),
    ("prayagraj",     "Prayagraj",           25.4358, 81.8463, 76.0, "mixed"),
    ("meerut",        "Meerut",              28.9845, 77.7064, 86.0, "traffic_corridor"),
    ("ghaziabad",     "Ghaziabad",           28.6692, 77.4538, 96.0, "industrial"),
    ("noida",         "Noida",               28.5355, 77.3910, 90.0, "commercial"),
    ("gurugram",      "Gurugram",            28.4595, 77.0266, 88.0, "commercial"),
    ("faridabad",     "Faridabad",           28.4089, 77.3178, 92.0, "industrial"),
    ("patna",         "Patna",               25.5941, 85.1376, 84.0, "mixed"),
    ("muzaffarpur",   "Muzaffarpur",         26.1209, 85.3647, 82.0, "mixed"),
    ("gaya",          "Gaya",                24.7955, 85.0002, 78.0, "mixed"),

    # ── Punjab, Haryana, the hills ──
    ("ludhiana",      "Ludhiana",            30.9010, 75.8573, 66.0, "industrial"),
    ("amritsar",      "Amritsar",            31.6340, 74.8723, 62.0, "mixed"),
    ("jalandhar",     "Jalandhar",           31.3260, 75.5762, 60.0, "mixed"),
    ("chandigarh",    "Chandigarh",          30.7333, 76.7794, 52.0, "commercial"),
    ("dehradun",      "Dehradun",            30.3165, 78.0322, 48.0, "mixed"),
    ("shimla",        "Shimla",              31.1048, 77.1734, 24.0, "green"),
    ("jammu",         "Jammu",               32.7266, 74.8570, 50.0, "mixed"),
    ("srinagar",      "Srinagar",            34.0837, 74.7973, 42.0, "mixed"),

    # ── Rajasthan & Gujarat ──
    ("jaipur",        "Jaipur",              26.9124, 75.7873, 62.0, "mixed"),
    ("jodhpur",       "Jodhpur",             26.2389, 73.0243, 58.0, "mixed"),
    ("kota",          "Kota",                25.2138, 75.8648, 56.0, "industrial"),
    ("udaipur",       "Udaipur",             24.5854, 73.7125, 44.0, "mixed"),
    ("ajmer",         "Ajmer",               26.4499, 74.6399, 50.0, "mixed"),
    ("ahmedabad",     "Ahmedabad",           23.0225, 72.5714, 58.0, "industrial"),
    ("surat",         "Surat",               21.1702, 72.8311, 52.0, "industrial"),
    ("vadodara",      "Vadodara",            22.3072, 73.1812, 50.0, "industrial"),
    ("rajkot",        "Rajkot",              22.3039, 70.8022, 46.0, "mixed"),

    # ── Central India ──
    ("bhopal",        "Bhopal",              23.2599, 77.4126, 52.0, "mixed"),
    ("indore",        "Indore",              22.7196, 75.8577, 54.0, "commercial"),
    ("gwalior",       "Gwalior",             26.2183, 78.1828, 72.0, "mixed"),
    ("jabalpur",      "Jabalpur",            23.1815, 79.9864, 50.0, "mixed"),
    ("nagpur",        "Nagpur",              21.1458, 79.0882, 48.0, "mixed"),
    ("raipur",        "Raipur",              21.2514, 81.6296, 60.0, "industrial"),
    ("bhilai",        "Bhilai",              21.1938, 81.3509, 64.0, "industrial"),

    # ── Maharashtra beyond Mumbai and Pune ──
    ("thane",         "Thane",               19.2183, 72.9781, 48.0, "commercial"),
    ("navi-mumbai",   "Navi Mumbai",         19.0330, 73.0297, 46.0, "commercial"),
    ("nashik",        "Nashik",              19.9975, 73.7898, 40.0, "mixed"),
    ("aurangabad",    "Chhatrapati Sambhajinagar", 19.8762, 75.3433, 42.0, "mixed"),
    ("solapur",       "Solapur",             17.6599, 75.9064, 40.0, "mixed"),
    ("kolhapur",      "Kolhapur",            16.7050, 74.2433, 36.0, "mixed"),

    # ── East ──
    ("kolkata",       "Kolkata",             22.5726, 88.3639, 66.0, "commercial"),
    ("howrah",        "Howrah",              22.5958, 88.2636, 70.0, "industrial"),
    ("asansol",       "Asansol",             23.6889, 86.9661, 68.0, "industrial"),
    ("ranchi",        "Ranchi",              23.3441, 85.3096, 48.0, "mixed"),
    ("jamshedpur",    "Jamshedpur",          22.8046, 86.2029, 58.0, "industrial"),
    ("dhanbad",       "Dhanbad",             23.7957, 86.4304, 74.0, "industrial"),
    ("bhubaneswar",   "Bhubaneswar",         20.2961, 85.8245, 42.0, "mixed"),
    ("cuttack",       "Cuttack",             20.4625, 85.8830, 44.0, "mixed"),
    ("guwahati",      "Guwahati",            26.1445, 91.7362, 54.0, "mixed"),
    ("siliguri",      "Siliguri",            26.7271, 88.3953, 50.0, "mixed"),

    # ── South ──
    ("chennai",       "Chennai",             13.0827, 80.2707, 40.0, "commercial"),
    ("coimbatore",    "Coimbatore",          11.0168, 76.9558, 34.0, "mixed"),
    ("madurai",       "Madurai",             9.9252,  78.1198, 32.0, "mixed"),
    ("hyderabad",     "Hyderabad",           17.3850, 78.4867, 44.0, "commercial"),
    ("visakhapatnam", "Visakhapatnam",       17.6868, 83.2185, 42.0, "industrial"),
    ("vijayawada",    "Vijayawada",          16.5062, 80.6480, 44.0, "mixed"),
    ("mysuru",        "Mysuru",              12.2958, 76.6394, 28.0, "mixed"),
    ("mangaluru",     "Mangaluru",           12.9141, 74.8560, 26.0, "mixed"),
    ("hubballi",      "Hubballi",            15.3647, 75.1240, 32.0, "mixed"),
    ("kochi",         "Kochi",               9.9312,  76.2673, 26.0, "mixed"),
    ("thiruvananthapuram", "Thiruvananthapuram", 8.5241, 76.9366, 24.0, "mixed"),
    ("kozhikode",     "Kozhikode",           11.2588, 75.7804, 25.0, "mixed"),
    ("panaji",        "Panaji",              15.4909, 73.8278, 22.0, "green"),
    ("puducherry",    "Puducherry",          11.9416, 79.8083, 30.0, "mixed"),
]


def _expand(entry: tuple[str, str, float, float, float, str]) -> dict:
    slug, name, lat, lon, _baseline, zone = entry
    code = slug.upper().replace("-", "")[:8] + "-C1"
    # Population exposed is unknown per-city here; the priority score treats a
    # missing value as a mid-range default rather than pretending to know.
    return {
        "slug": slug, "name": name, "country": "India",
        "latitude": lat, "longitude": lon, "population": None,
        "default_zoom": 11, "waqi_keyword": slug.replace("-", " "),
        "aqi_scale": "us_epa",
        "stations": [(code, f"{name} City Centre", lat, lon, zone, None,
                      zone in ("traffic_corridor", "commercial"),
                      zone == "industrial", False)],
    }


CITIES = CITIES + [_expand(entry) for entry in MORE_CITIES]

# Annual-mean PM2.5 per city, consumed by the synthetic model so the national
# map does not show every city at the same level.
CITY_BASELINES: dict[str, float] = {
    "delhi": 95.0, "mumbai": 46.0, "pune": 38.0, "bengaluru": 32.0,
    **{entry[0]: entry[4] for entry in MORE_CITIES},
}

# ── Intervention catalogue ────────────────────────────────────────────
# `effectiveness` = the fraction of THAT SOURCE's contribution to each pollutant
# which the lever removes at full magnitude. It is deliberately NOT the share of
# ambient pollution the source contributes — that comes from live attribution at
# each station, and the simulator multiplies the two. Keeping them separate is
# what stops the classic "cut traffic 30%, AQI drops 30%" error.
#
# Values are planning estimates informed by Indian source-apportionment work
# (SAFAR / TERI / IIT-Kanpur emission inventories) and are stored as data so a
# city can recalibrate them without a code change.

INTERVENTIONS = [
    {
        "key": "traffic_reduction", "label": "Reduce vehicular traffic volume",
        "category": "transport", "unit": "percent_reduction", "max_magnitude": 60.0,
        "description": "Odd-even schemes, congestion pricing, corridor closures or "
                       "diverting freight away from the affected zone.",
        "effectiveness": {"pm25": 0.85, "pm10": 0.70, "no2": 0.95, "co": 0.92,
                          "o3": 0.25, "so2": 0.10},
        "lag_hours": 3, "cost_band": "medium",
        "evidence_note": "Removing vehicles removes tailpipe emissions almost "
                         "completely but only part of the resuspended road dust "
                         "they stir up, so PM10 responds less than NO₂. Ozone is "
                         "secondary and can even rise locally when NOx falls.",
    },
    {
        "key": "industrial_emission_control", "label": "Curb industrial emissions",
        "category": "industry", "unit": "percent_reduction", "max_magnitude": 50.0,
        "description": "Temporary load reduction, scrubber enforcement and shutdown "
                       "of non-compliant units in the affected airshed.",
        "effectiveness": {"pm25": 0.80, "pm10": 0.72, "no2": 0.65, "so2": 0.95,
                          "co": 0.45, "o3": 0.15},
        "lag_hours": 12, "cost_band": "high",
        "evidence_note": "SO₂ is almost entirely industrial in origin, so this "
                         "lever is near-complete for SO₂ and partial for PM.",
    },
    {
        "key": "construction_halt", "label": "Pause construction activity",
        "category": "construction", "unit": "percent_reduction", "max_magnitude": 100.0,
        "description": "Stop-work orders on earthworks, demolition and material "
                       "handling within the hotspot.",
        "effectiveness": {"pm25": 0.55, "pm10": 0.85, "no2": 0.20, "so2": 0.10,
                          "co": 0.15, "o3": 0.0},
        "lag_hours": 6, "cost_band": "medium",
        "evidence_note": "Construction dust is coarse-fraction dominated, so a "
                         "halt removes far more PM10 than PM2.5.",
    },
    {
        "key": "road_dust_suppression", "label": "Intensify road-dust suppression",
        "category": "dust", "unit": "percent_effectiveness", "max_magnitude": 100.0,
        "description": "Mechanised sweeping, water sprinkling and anti-smog guns on "
                       "high-traffic corridors.",
        "effectiveness": {"pm25": 0.30, "pm10": 0.60, "no2": 0.0, "so2": 0.0,
                          "co": 0.0, "o3": 0.0},
        "lag_hours": 2, "cost_band": "low",
        "evidence_note": "Suppresses resuspension only, and the benefit decays "
                         "within hours unless the treatment is repeated.",
    },
    {
        "key": "public_transport_boost", "label": "Increase public transport capacity",
        "category": "transport", "unit": "percent_increase", "max_magnitude": 50.0,
        "description": "Extra bus/metro frequency and fare relief to shift trips off "
                       "private vehicles.",
        "effectiveness": {"pm25": 0.28, "pm10": 0.22, "no2": 0.34, "co": 0.32,
                          "so2": 0.05, "o3": 0.08},
        "lag_hours": 24, "cost_band": "medium",
        "evidence_note": "Modal shift is partial: a 50% capacity increase does not "
                         "remove anything like 50% of car trips, so effectiveness "
                         "against the traffic source is well below 1.",
    },
    {
        "key": "biomass_burning_control", "label": "Suppress open/biomass burning",
        "category": "burning", "unit": "percent_reduction", "max_magnitude": 100.0,
        "description": "Enforcement against waste and crop-residue burning plus "
                       "alternatives for winter heating fires.",
        "effectiveness": {"pm25": 0.88, "pm10": 0.70, "co": 0.85, "no2": 0.30,
                          "so2": 0.15, "o3": 0.10},
        "lag_hours": 4, "cost_band": "low",
        "evidence_note": "Enforcement is effective where it reaches, but local "
                         "action cannot touch regional transported smoke.",
    },
]
