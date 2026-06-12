"""Curated seed tickers for markets the yfinance screener does not serve (PH, VN).

These are validated live in build_universe.py; non-resolving names are logged and dropped,
never fabricated. SG/ID/MY/TH are sourced from the yfinance region screener instead.
"""

PH_SEEDS = [
    "SM", "BDO", "BPI", "MBT", "ALI", "AC", "JFC", "URC", "TEL", "GLO",
    "AEV", "AP", "MER", "ICT", "JGS", "SMC", "DMC", "RRHI", "SECB", "CNVRG",
    "MONDE", "GTCAP", "BLOOM", "PGOLD", "FGEN", "LTG", "SCC", "AGI", "MWIDE", "FB",
    "NIKL", "COSCO", "RLC", "MEG", "SMPH", "EMP", "PX", "ACEN", "WLCON", "CEB",
]

VN_SEEDS = [
    "VIC", "VHM", "VCB", "BID", "CTG", "TCB", "VPB", "MBB", "ACB", "HPG",
    "VNM", "MSN", "MWG", "FPT", "GAS", "PLX", "SAB", "VRE", "VJC", "POW",
    "SSI", "HDB", "STB", "TPB", "VIB", "SHB", "NVL", "PDR", "GVR", "BCM",
    "DGC", "REE", "DHG", "PNJ", "KDH", "VCI", "VND", "HSG", "DXG", "GMD",
]

# Real company names for VN seed codes — the screener gives no longName for VN, so the universe
# carries bare codes; GDELT needs a real name to query. Used by the GDELT fetcher for country=Vietnam.
VN_NAMES = {
    "VIC": "Vingroup", "VHM": "Vinhomes", "VCB": "Vietcombank", "BID": "BIDV",
    "CTG": "VietinBank", "TCB": "Techcombank", "VPB": "VPBank", "MBB": "MB Bank",
    "ACB": "Asia Commercial Bank", "HPG": "Hoa Phat Group", "VNM": "Vinamilk",
    "MSN": "Masan Group", "MWG": "Mobile World", "FPT": "FPT Corporation",
    "GAS": "PetroVietnam Gas", "PLX": "Petrolimex", "SAB": "Sabeco", "VRE": "Vincom Retail",
    "VJC": "Vietjet Air", "POW": "PetroVietnam Power", "SSI": "SSI Securities", "HDB": "HDBank",
    "STB": "Sacombank", "TPB": "TPBank", "VIB": "Vietnam International Bank",
    "SHB": "Saigon Hanoi Bank", "NVL": "Novaland", "PDR": "Phat Dat Real Estate",
    "GVR": "Vietnam Rubber Group", "BCM": "Becamex IDC", "DGC": "Duc Giang Chemicals",
    "REE": "Refrigeration Electrical Engineering", "DHG": "DHG Pharma",
    "PNJ": "Phu Nhuan Jewelry", "KDH": "Khang Dien House", "VCI": "Vietcap Securities",
    "VND": "VNDirect", "HSG": "Hoa Sen Group", "DXG": "Dat Xanh Group", "GMD": "Gemadept",
}

# Country -> (yahoo suffix, list of bare seed codes)
# NOTE: Philippines (.PS / .PH / .PSE) does not resolve on yfinance under any suffix
# (verified 2026-06-12) — dropped and documented (RESEARCH_LOG, BIAS_REGISTER B-05). PH_SEEDS
# retained for the CSV-import upgrade path. Universe therefore spans 5 of 6 ASEAN markets.
SEED_MARKETS = {
    "Vietnam": (".VN", VN_SEEDS),
}
