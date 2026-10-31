"""The wider Indian city list and the state each city belongs to.

``seed_data.MORE_CITIES`` carried the first 67 single-receptor cities; this
module adds the rest of the country so the national view covers 200+ cities.
Each entry follows the same tuple shape:

    (slug, display name, lat, lon, annual-mean PM2.5 baseline ug/m3, zone)

The baseline is only used by the labelled demo model. Live numbers come from
the monitoring stations nearest each city (see ``services.live_air``).
"""
from __future__ import annotations

EXTRA_CITIES: list[tuple[str, str, float, float, float, str]] = [
    # ── Uttar Pradesh ──
    ("greater-noida",  "Greater Noida",   28.4744, 77.5040, 88.0, "industrial"),
    ("bareilly",       "Bareilly",        28.3670, 79.4304, 70.0, "mixed"),
    ("aligarh",        "Aligarh",         27.8974, 78.0880, 76.0, "mixed"),
    ("moradabad",      "Moradabad",       28.8386, 78.7733, 78.0, "industrial"),
    ("gorakhpur",      "Gorakhpur",       26.7606, 83.3732, 72.0, "mixed"),
    ("saharanpur",     "Saharanpur",      29.9680, 77.5552, 66.0, "mixed"),
    ("jhansi",         "Jhansi",          25.4484, 78.5685, 60.0, "mixed"),
    ("mathura",        "Mathura",         27.4924, 77.6737, 72.0, "mixed"),
    ("firozabad",      "Firozabad",       27.1592, 78.3957, 76.0, "industrial"),
    ("muzaffarnagar",  "Muzaffarnagar",   29.4727, 77.7085, 80.0, "industrial"),
    ("hapur",          "Hapur",           28.7306, 77.7759, 86.0, "mixed"),
    ("bulandshahr",    "Bulandshahr",     28.4069, 77.8498, 80.0, "mixed"),
    ("baghpat",        "Baghpat",         28.9448, 77.2185, 84.0, "mixed"),
    ("ayodhya",        "Ayodhya",         26.7922, 82.1998, 66.0, "mixed"),
    ("rampur",         "Rampur",          28.8090, 79.0250, 70.0, "mixed"),
    ("shahjahanpur",   "Shahjahanpur",    27.8830, 79.9120, 68.0, "mixed"),
    ("etawah",         "Etawah",          26.7856, 79.0158, 70.0, "mixed"),
    ("mirzapur",       "Mirzapur",        25.1460, 82.5690, 64.0, "mixed"),
    ("unnao",          "Unnao",           26.5393, 80.4878, 80.0, "industrial"),

    # ── Haryana ──
    ("panipat",        "Panipat",         29.3909, 76.9635, 80.0, "industrial"),
    ("sonipat",        "Sonipat",         28.9931, 77.0151, 82.0, "industrial"),
    ("rohtak",         "Rohtak",          28.8955, 76.6066, 76.0, "mixed"),
    ("hisar",          "Hisar",           29.1492, 75.7217, 72.0, "mixed"),
    ("karnal",         "Karnal",          29.6857, 76.9905, 68.0, "mixed"),
    ("ambala",         "Ambala",          30.3782, 76.7767, 58.0, "mixed"),
    ("yamunanagar",    "Yamunanagar",     30.1290, 77.2674, 64.0, "industrial"),
    ("bhiwani",        "Bhiwani",         28.7975, 76.1322, 74.0, "mixed"),
    ("kurukshetra",    "Kurukshetra",     29.9695, 76.8783, 64.0, "mixed"),
    ("sirsa",          "Sirsa",           29.5349, 75.0292, 66.0, "mixed"),
    ("bahadurgarh",    "Bahadurgarh",     28.6920, 76.9240, 86.0, "industrial"),
    ("jind",           "Jind",            29.3159, 76.3144, 72.0, "mixed"),
    ("fatehabad",      "Fatehabad",       29.5152, 75.4550, 68.0, "mixed"),
    ("charkhi-dadri",  "Charkhi Dadri",   28.5921, 76.2653, 76.0, "mixed"),
    ("palwal",         "Palwal",          28.1487, 77.3320, 80.0, "mixed"),
    ("rewari",         "Rewari",          28.1990, 76.6190, 74.0, "mixed"),
    ("kaithal",        "Kaithal",         29.8015, 76.3998, 70.0, "mixed"),
    ("narnaul",        "Narnaul",         28.0444, 76.1080, 70.0, "mixed"),

    # ── Punjab ──
    ("patiala",        "Patiala",         30.3398, 76.3869, 58.0, "mixed"),
    ("bathinda",       "Bathinda",        30.2110, 74.9455, 60.0, "industrial"),
    ("mohali",         "Mohali",          30.7046, 76.7179, 50.0, "commercial"),
    ("khanna",         "Khanna",          30.7050, 76.2210, 62.0, "industrial"),
    ("mandi-gobindgarh", "Mandi Gobindgarh", 30.6720, 76.2940, 66.0, "industrial"),

    # ── Rajasthan ──
    ("bikaner",        "Bikaner",         28.0229, 73.3119, 60.0, "mixed"),
    ("alwar",          "Alwar",           27.5530, 76.6346, 64.0, "mixed"),
    ("bhiwadi",        "Bhiwadi",         28.2100, 76.8600, 86.0, "industrial"),
    ("bharatpur",      "Bharatpur",       27.2152, 77.4890, 66.0, "mixed"),
    ("sikar",          "Sikar",           27.6094, 75.1399, 58.0, "mixed"),
    ("pali",           "Pali",            25.7711, 73.3234, 56.0, "industrial"),
    ("bhilwara",       "Bhilwara",        25.3407, 74.6313, 54.0, "industrial"),
    ("sri-ganganagar", "Sri Ganganagar",  29.9038, 73.8772, 62.0, "mixed"),
    ("chittorgarh",    "Chittorgarh",     24.8887, 74.6269, 50.0, "mixed"),

    # ── Gujarat ──
    ("gandhinagar",    "Gandhinagar",     23.2156, 72.6369, 50.0, "green"),
    ("bhavnagar",      "Bhavnagar",       21.7645, 72.1519, 46.0, "mixed"),
    ("jamnagar",       "Jamnagar",        22.4707, 70.0577, 44.0, "industrial"),
    ("junagadh",       "Junagadh",        21.5222, 70.4579, 40.0, "mixed"),
    ("ankleshwar",     "Ankleshwar",      21.6264, 73.0151, 56.0, "industrial"),
    ("vapi",           "Vapi",            20.3893, 72.9106, 54.0, "industrial"),
    ("anand",          "Anand",           22.5645, 72.9289, 46.0, "mixed"),
    ("bharuch",        "Bharuch",         21.7051, 72.9959, 50.0, "industrial"),
    ("gandhidham",     "Gandhidham",      23.0753, 70.1337, 48.0, "industrial"),

    # ── Madhya Pradesh ──
    ("ujjain",         "Ujjain",          23.1765, 75.7885, 50.0, "mixed"),
    ("sagar",          "Sagar",           23.8388, 78.7378, 46.0, "mixed"),
    ("dewas",          "Dewas",           22.9676, 76.0534, 50.0, "industrial"),
    ("satna",          "Satna",           24.6005, 80.8322, 54.0, "industrial"),
    ("ratlam",         "Ratlam",          23.3315, 75.0367, 48.0, "mixed"),
    ("singrauli",      "Singrauli",       24.1997, 82.6754, 62.0, "industrial"),
    ("katni",          "Katni",           23.8343, 80.3894, 54.0, "industrial"),
    ("pithampur",      "Pithampur",       22.6130, 75.6790, 56.0, "industrial"),
    ("rewa",           "Rewa",            24.5362, 81.3037, 52.0, "mixed"),

    # ── Maharashtra ──
    ("amravati",       "Amravati",        20.9320, 77.7523, 40.0, "mixed"),
    ("akola",          "Akola",           20.7002, 77.0082, 42.0, "mixed"),
    ("jalgaon",        "Jalgaon",         21.0077, 75.5626, 42.0, "mixed"),
    ("chandrapur",     "Chandrapur",      19.9615, 79.2961, 54.0, "industrial"),
    ("latur",          "Latur",           18.4088, 76.5604, 38.0, "mixed"),
    ("sangli",         "Sangli",          16.8524, 74.5815, 36.0, "mixed"),
    ("nanded",         "Nanded",          19.1383, 77.3210, 40.0, "mixed"),
    ("ahmednagar",     "Ahilyanagar",     19.0948, 74.7480, 38.0, "mixed"),
    ("kalyan",         "Kalyan-Dombivli", 19.2437, 73.1355, 50.0, "mixed"),
    ("vasai-virar",    "Vasai-Virar",     19.4259, 72.8225, 44.0, "mixed"),
    ("dhule",          "Dhule",           20.9042, 74.7749, 40.0, "mixed"),
    ("jalna",          "Jalna",           19.8347, 75.8816, 40.0, "industrial"),
    ("parbhani",       "Parbhani",        19.2610, 76.7748, 38.0, "mixed"),
    ("bhiwandi",       "Bhiwandi",        19.2813, 73.0483, 52.0, "industrial"),
    ("mira-bhayandar", "Mira-Bhayandar",  19.2952, 72.8544, 46.0, "mixed"),
    ("ulhasnagar",     "Ulhasnagar",      19.2215, 73.1645, 50.0, "industrial"),
    ("satara",         "Satara",          17.6805, 74.0183, 32.0, "mixed"),
    ("ratnagiri",      "Ratnagiri",       16.9902, 73.3120, 28.0, "green"),

    # ── Bihar ──
    ("bhagalpur",      "Bhagalpur",       25.2425, 86.9842, 74.0, "mixed"),
    ("darbhanga",      "Darbhanga",       26.1542, 85.8918, 76.0, "mixed"),
    ("purnia",         "Purnia",          25.7771, 87.4753, 70.0, "mixed"),
    ("begusarai",      "Begusarai",       25.4182, 86.1272, 78.0, "industrial"),
    ("arrah",          "Arrah",           25.5560, 84.6603, 76.0, "mixed"),
    ("bihar-sharif",   "Bihar Sharif",    25.1982, 85.5149, 78.0, "mixed"),
    ("hajipur",        "Hajipur",         25.6858, 85.2146, 80.0, "mixed"),
    ("motihari",       "Motihari",        26.6470, 84.9167, 72.0, "mixed"),
    ("chhapra",        "Chhapra",         25.7812, 84.7478, 76.0, "mixed"),
    ("sasaram",        "Sasaram",         24.9500, 84.0300, 72.0, "mixed"),
    ("katihar",        "Katihar",         25.5390, 87.5700, 70.0, "mixed"),
    ("kishanganj",     "Kishanganj",      26.1052, 87.9425, 64.0, "mixed"),

    # ── Jharkhand ──
    ("bokaro",         "Bokaro Steel City", 23.6693, 86.1511, 66.0, "industrial"),
    ("hazaribagh",     "Hazaribagh",      23.9966, 85.3691, 52.0, "mixed"),
    ("deoghar",        "Deoghar",         24.4854, 86.6947, 54.0, "mixed"),

    # ── West Bengal ──
    ("durgapur",       "Durgapur",        23.5204, 87.3119, 66.0, "industrial"),
    ("haldia",         "Haldia",          22.0667, 88.0698, 58.0, "industrial"),
    ("kharagpur",      "Kharagpur",       22.3460, 87.2320, 54.0, "mixed"),
    ("bardhaman",      "Bardhaman",       23.2324, 87.8615, 60.0, "mixed"),
    ("malda",          "Malda",           25.0108, 88.1411, 62.0, "mixed"),
    ("barrackpore",    "Barrackpore",     22.7640, 88.3776, 64.0, "mixed"),
    ("kalyani",        "Kalyani",         22.9751, 88.4345, 58.0, "mixed"),
    ("salt-lake",      "Bidhannagar (Salt Lake)", 22.5800, 88.4140, 60.0, "commercial"),
    ("darjeeling",     "Darjeeling",      27.0410, 88.2663, 30.0, "green"),

    # ── Odisha ──
    ("rourkela",       "Rourkela",        22.2604, 84.8536, 58.0, "industrial"),
    ("sambalpur",      "Sambalpur",       21.4669, 83.9812, 50.0, "mixed"),
    ("talcher",        "Talcher",         20.9500, 85.2300, 62.0, "industrial"),
    ("angul",          "Angul",           20.8400, 85.1000, 60.0, "industrial"),
    ("berhampur",      "Berhampur",       19.3150, 84.7941, 38.0, "mixed"),
    ("balasore",       "Balasore",        21.4942, 86.9317, 42.0, "mixed"),

    # ── Chhattisgarh ──
    ("bilaspur",       "Bilaspur",        22.0797, 82.1391, 56.0, "mixed"),
    ("korba",          "Korba",           22.3595, 82.7501, 64.0, "industrial"),
    ("raigarh",        "Raigarh",         21.8974, 83.3950, 58.0, "industrial"),

    # ── North-east ──
    ("shillong",       "Shillong",        25.5788, 91.8933, 30.0, "green"),
    ("agartala",       "Agartala",        23.8315, 91.2868, 48.0, "mixed"),
    ("imphal",         "Imphal",          24.8170, 93.9368, 42.0, "mixed"),
    ("aizawl",         "Aizawl",          23.7271, 92.7176, 26.0, "green"),
    ("kohima",         "Kohima",          25.6751, 94.1086, 30.0, "green"),
    ("itanagar",       "Itanagar",        27.0844, 93.6053, 28.0, "green"),
    ("gangtok",        "Gangtok",         27.3389, 88.6065, 24.0, "green"),
    ("silchar",        "Silchar",         24.8333, 92.7789, 44.0, "mixed"),
    ("dibrugarh",      "Dibrugarh",       27.4728, 94.9120, 40.0, "mixed"),
    ("nagaon",         "Nagaon",          26.3480, 92.6838, 44.0, "mixed"),
    ("jorhat",         "Jorhat",          26.7509, 94.2037, 38.0, "mixed"),

    # ── Tamil Nadu ──
    ("tiruchirappalli", "Tiruchirappalli", 10.7905, 78.7047, 32.0, "mixed"),
    ("salem",          "Salem",           11.6643, 78.1460, 32.0, "mixed"),
    ("tirunelveli",    "Tirunelveli",     8.7139,  77.7567, 28.0, "mixed"),
    ("tiruppur",       "Tiruppur",        11.1085, 77.3411, 34.0, "industrial"),
    ("vellore",        "Vellore",         12.9165, 79.1325, 32.0, "mixed"),
    ("erode",          "Erode",           11.3410, 77.7172, 32.0, "mixed"),
    ("thoothukudi",    "Thoothukudi",     8.7642,  78.1348, 34.0, "industrial"),
    ("thanjavur",      "Thanjavur",       10.7870, 79.1378, 28.0, "mixed"),
    ("hosur",          "Hosur",           12.7409, 77.8253, 36.0, "industrial"),
    ("kanchipuram",    "Kanchipuram",     12.8342, 79.7036, 32.0, "mixed"),
    ("ooty",           "Ooty",            11.4102, 76.6950, 18.0, "green"),
    ("cuddalore",      "Cuddalore",       11.7480, 79.7714, 32.0, "industrial"),
    ("dindigul",       "Dindigul",        10.3673, 77.9803, 28.0, "mixed"),
    ("nagercoil",      "Nagercoil",       8.1833,  77.4119, 24.0, "mixed"),

    # ── Karnataka ──
    ("belagavi",       "Belagavi",        15.8497, 74.4977, 30.0, "mixed"),
    ("kalaburagi",     "Kalaburagi",      17.3297, 76.8343, 36.0, "mixed"),
    ("davanagere",     "Davanagere",      14.4644, 75.9218, 32.0, "mixed"),
    ("ballari",        "Ballari",         15.1394, 76.9214, 40.0, "industrial"),
    ("vijayapura",     "Vijayapura",      16.8302, 75.7100, 34.0, "mixed"),
    ("shivamogga",     "Shivamogga",      13.9299, 75.5681, 26.0, "mixed"),
    ("tumakuru",       "Tumakuru",        13.3379, 77.1173, 30.0, "mixed"),
    ("udupi",          "Udupi",           13.3409, 74.7421, 22.0, "green"),
    ("raichur",        "Raichur",         16.2120, 77.3439, 36.0, "industrial"),
    ("bidar",          "Bidar",           17.9104, 77.5199, 34.0, "mixed"),
    ("hassan",         "Hassan",          13.0072, 76.0962, 24.0, "mixed"),
    ("chikkaballapur", "Chikkaballapur",  13.4355, 77.7315, 28.0, "mixed"),
    ("dharwad",        "Dharwad",         15.4589, 75.0078, 30.0, "mixed"),

    # ── Telangana ──
    ("warangal",       "Warangal",        17.9689, 79.5941, 38.0, "mixed"),
    ("karimnagar",     "Karimnagar",      18.4386, 79.1288, 36.0, "mixed"),
    ("nizamabad",      "Nizamabad",       18.6725, 78.0941, 36.0, "mixed"),
    ("khammam",        "Khammam",         17.2473, 80.1514, 36.0, "mixed"),
    ("ramagundam",     "Ramagundam",      18.7550, 79.4740, 44.0, "industrial"),
    ("sangareddy",     "Sangareddy",      17.6140, 78.0816, 40.0, "industrial"),

    # ── Andhra Pradesh ──
    ("guntur",         "Guntur",          16.3067, 80.4365, 40.0, "mixed"),
    ("nellore",        "Nellore",         14.4426, 79.9865, 34.0, "mixed"),
    ("tirupati",       "Tirupati",        13.6288, 79.4192, 32.0, "mixed"),
    ("kurnool",        "Kurnool",         15.8281, 78.0373, 36.0, "mixed"),
    ("kakinada",       "Kakinada",        16.9891, 82.2475, 34.0, "industrial"),
    ("rajahmundry",    "Rajamahendravaram", 17.0005, 81.8040, 36.0, "mixed"),
    ("anantapur",      "Anantapur",       14.6819, 77.6006, 34.0, "mixed"),
    ("kadapa",         "Kadapa",          14.4673, 78.8242, 34.0, "mixed"),
    ("eluru",          "Eluru",           16.7107, 81.0952, 36.0, "mixed"),
    ("ongole",         "Ongole",          15.5057, 80.0499, 32.0, "mixed"),
    ("vizianagaram",   "Vizianagaram",    18.1067, 83.3956, 34.0, "mixed"),

    # ── Kerala ──
    ("thrissur",       "Thrissur",        10.5276, 76.2144, 24.0, "mixed"),
    ("kollam",         "Kollam",          8.8932,  76.6141, 22.0, "mixed"),
    ("kannur",         "Kannur",          11.8745, 75.3704, 22.0, "mixed"),
    ("kottayam",       "Kottayam",        9.5916,  76.5222, 22.0, "green"),
    ("palakkad",       "Palakkad",        10.7867, 76.6548, 26.0, "mixed"),
    ("alappuzha",      "Alappuzha",       9.4981,  76.3388, 20.0, "green"),
    ("malappuram",     "Malappuram",      11.0510, 76.0711, 22.0, "mixed"),
    ("eloor",          "Eloor",           10.0750, 76.3000, 30.0, "industrial"),

    # ── Goa ──
    ("vasco-da-gama",  "Vasco da Gama",   15.3860, 73.8440, 26.0, "industrial"),
    ("margao",         "Margao",          15.2832, 73.9862, 22.0, "mixed"),

    # ── Uttarakhand ──
    ("haridwar",       "Haridwar",        29.9457, 78.1642, 54.0, "mixed"),
    ("rishikesh",      "Rishikesh",       30.0869, 78.2676, 42.0, "green"),
    ("haldwani",       "Haldwani",        29.2183, 79.5130, 50.0, "mixed"),
    ("rudrapur",       "Rudrapur",        28.9845, 79.4006, 58.0, "industrial"),
    ("roorkee",        "Roorkee",         29.8543, 77.8880, 58.0, "mixed"),
    ("kashipur",       "Kashipur",        29.2104, 78.9619, 60.0, "industrial"),

    # ── Himachal Pradesh ──
    ("dharamshala",    "Dharamshala",     32.2190, 76.3234, 22.0, "green"),
    ("baddi",          "Baddi",           30.9578, 76.7914, 56.0, "industrial"),
    ("manali",         "Manali",          32.2432, 77.1892, 16.0, "green"),
    ("solan",          "Solan",           30.9045, 77.0967, 28.0, "mixed"),
    ("paonta-sahib",   "Paonta Sahib",    30.4384, 77.6241, 44.0, "industrial"),

    # ── Jammu & Kashmir, Ladakh ──
    ("leh",            "Leh",             34.1526, 77.5771, 18.0, "green"),
    ("anantnag",       "Anantnag",        33.7311, 75.1487, 38.0, "mixed"),
    ("kathua",         "Kathua",          32.3700, 75.5200, 50.0, "mixed"),

    # ── Union territories ──
    ("port-blair",     "Port Blair",      11.6234, 92.7265, 16.0, "green"),
    ("daman",          "Daman",           20.3974, 72.8328, 42.0, "industrial"),
    ("silvassa",       "Silvassa",        20.2766, 73.0169, 46.0, "industrial"),
]

# State / UT of every seeded city (including the original 71).
STATE_OF: dict[str, str] = {
    # metros and the original list
    "delhi": "Delhi", "mumbai": "Maharashtra", "pune": "Maharashtra",
    "bengaluru": "Karnataka",
    "kanpur": "Uttar Pradesh", "lucknow": "Uttar Pradesh", "agra": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "meerut": "Uttar Pradesh", "ghaziabad": "Uttar Pradesh", "noida": "Uttar Pradesh",
    "gurugram": "Haryana", "faridabad": "Haryana",
    "patna": "Bihar", "muzaffarpur": "Bihar", "gaya": "Bihar",
    "ludhiana": "Punjab", "amritsar": "Punjab", "jalandhar": "Punjab",
    "chandigarh": "Chandigarh", "dehradun": "Uttarakhand",
    "shimla": "Himachal Pradesh", "jammu": "Jammu & Kashmir",
    "srinagar": "Jammu & Kashmir",
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "kota": "Rajasthan",
    "udaipur": "Rajasthan", "ajmer": "Rajasthan",
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "rajkot": "Gujarat",
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh", "jabalpur": "Madhya Pradesh",
    "nagpur": "Maharashtra", "raipur": "Chhattisgarh", "bhilai": "Chhattisgarh",
    "thane": "Maharashtra", "navi-mumbai": "Maharashtra", "nashik": "Maharashtra",
    "aurangabad": "Maharashtra", "solapur": "Maharashtra", "kolhapur": "Maharashtra",
    "kolkata": "West Bengal", "howrah": "West Bengal", "asansol": "West Bengal",
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand", "dhanbad": "Jharkhand",
    "bhubaneswar": "Odisha", "cuttack": "Odisha", "guwahati": "Assam",
    "siliguri": "West Bengal",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "hyderabad": "Telangana", "visakhapatnam": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh", "mysuru": "Karnataka", "mangaluru": "Karnataka",
    "hubballi": "Karnataka", "kochi": "Kerala", "thiruvananthapuram": "Kerala",
    "kozhikode": "Kerala", "panaji": "Goa", "puducherry": "Puducherry",
}

_SECTION_STATE = [
    ("greater-noida", "unnao", "Uttar Pradesh"),
    ("panipat", "narnaul", "Haryana"),
    ("patiala", "mandi-gobindgarh", "Punjab"),
    ("bikaner", "chittorgarh", "Rajasthan"),
    ("gandhinagar", "gandhidham", "Gujarat"),
    ("ujjain", "rewa", "Madhya Pradesh"),
    ("amravati", "ratnagiri", "Maharashtra"),
    ("bhagalpur", "kishanganj", "Bihar"),
    ("bokaro", "deoghar", "Jharkhand"),
    ("durgapur", "darjeeling", "West Bengal"),
    ("rourkela", "balasore", "Odisha"),
    ("bilaspur", "raigarh", "Chhattisgarh"),
    ("tiruchirappalli", "nagercoil", "Tamil Nadu"),
    ("belagavi", "dharwad", "Karnataka"),
    ("warangal", "sangareddy", "Telangana"),
    ("guntur", "vizianagaram", "Andhra Pradesh"),
    ("thrissur", "eloor", "Kerala"),
    ("vasco-da-gama", "margao", "Goa"),
    ("haridwar", "kashipur", "Uttarakhand"),
    ("dharamshala", "paonta-sahib", "Himachal Pradesh"),
    ("anantnag", "kathua", "Jammu & Kashmir"),
]
_slugs = [entry[0] for entry in EXTRA_CITIES]
for _first, _last, _state in _SECTION_STATE:
    for _slug in _slugs[_slugs.index(_first):_slugs.index(_last) + 1]:
        STATE_OF[_slug] = _state

STATE_OF.update({
    "leh": "Ladakh", "port-blair": "Andaman & Nicobar",
    "daman": "Dadra & Nagar Haveli and Daman & Diu",
    "silvassa": "Dadra & Nagar Haveli and Daman & Diu",
    "shillong": "Meghalaya", "agartala": "Tripura", "imphal": "Manipur",
    "aizawl": "Mizoram", "kohima": "Nagaland", "itanagar": "Arunachal Pradesh",
    "gangtok": "Sikkim", "silchar": "Assam", "dibrugarh": "Assam",
    "nagaon": "Assam", "jorhat": "Assam",
})

# How far (km) from the city centre a monitoring station may be and still
# count as "in" the city. Metros sprawl; small towns do not.
METRO_RADIUS_KM: dict[str, float] = {
    "delhi": 30.0, "mumbai": 28.0, "kolkata": 22.0, "chennai": 22.0,
    "bengaluru": 22.0, "hyderabad": 22.0, "pune": 18.0, "ahmedabad": 18.0,
}
