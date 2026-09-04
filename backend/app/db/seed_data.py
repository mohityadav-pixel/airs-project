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
