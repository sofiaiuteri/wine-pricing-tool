import math
import pandas as pd
import streamlit as st
import numpy as np

st.set_page_config(page_title="Wine Pricing Tool", layout="wide")
st.title("🍷 Wine Pricing Tool")

# ---- Sidebar (editable rules) ----
with st.sidebar:
    st.header("Bottle bands")
    EntryMax      = st.number_input("EntryMax (<)", value=50.0)
    MidMin        = st.number_input("MidMin (≥)", value=50.0)
    MidMax        = st.number_input("MidMax (≤)", value=80.0)
    PremiumMin    = st.number_input("PremiumMin (>)", value=120.0)

    st.subheader("Entry (retail < EntryMax)")
    EntryMultiple = st.number_input("EntryMultiple (×)", value=2.40, step=0.05)

    st.subheader("Mid (MidMin–MidMax)")
    MidMultiple   = st.number_input("MidMultiple (×)", value=2.10, step=0.05)

    st.subheader("Upper-Mid (MidMax–PremiumMin)")
    UM_Method     = st.selectbox("Upper-Mid Method", ["MULT","ADDON"], index=0)
    UMMultiple    = st.number_input("Upper-Mid Multiple (×)", value=1.80, step=0.05)
    UMAddOn       = st.number_input("Upper-Mid AddOn ($)", value=50.0, step=5.0)

    st.subheader("Premium (> PremiumMin)")
    PremiumAddOn  = st.number_input("PremiumAddOn (+$)", value=100.0, step=5.0)
    PremiumMult   = st.number_input("PremiumMult (×)", value=1.50, step=0.05)
    PremiumChoice = st.selectbox("PremiumChoice", ["HIGHER","ADDON","MULT"])

    st.divider()
    st.header("Category tweaks")
    # If you want white ~10–15% below red, increase this so red is higher within tier.
    RedBump       = st.number_input("RedBump (adds to multiple)", value=0.10, step=0.05, help="Add to multiple for Red in Entry/Mid/Upper-Mid")

    st.divider()
    st.header("Glass program")
    GlassServings = st.number_input("GlassServings per bottle", value=5, step=1)
    GlassCap        = st.number_input("Glass cap ($)", value=21, step=1)
    FloorRedSpark   = st.number_input("Glass floor – Red/Sparkling", value=16, step=1)
    FloorWhiteRose  = st.number_input("Glass floor – White/Rosé", value=15, step=1)

    st.divider()
    st.header("Diagnostics (targets)")
    Target120 = st.number_input("Target multiple for 5 glasses (e.g., 1.20)", value=1.20, step=0.01)
    Target125 = st.number_input("Second target (e.g., 1.25)", value=1.25, step=0.01)

# ---- Helpers ----
def round_to_5_or_9(x: float) -> int:
    """Nearest (half-up) to ...5 or ...9."""
    x = float(x)
    n5 = 5 * math.floor(x/5 + 0.5)
    n9 = 10 * math.floor((x-9)/10 + 0.5) + 9
    return int(n5 if abs(x-n5) <= abs(x-n9) else n9)

def ceil_to_5_or_9(x: float) -> int:
    """Ceiling to the next menu-friendly ...5 or ...9."""
    x = float(x)
    n5 = 5 * math.ceil(x/5)                 # next 5 ≥ x
    n9 = 10 * math.floor((x-9)/10) + 9      # 9 ≤ x
    if n9 < x:
        n9 += 10                            # next 9 ≥ x
    return int(min(n5, n9))

def coerce_bool(v) -> bool:
    s = str(v).strip().upper()
    return s in ("TRUE","1","YES","Y","T") or v is True

def color_floor_value(color: str, floor_rs: int, floor_wr: int) -> int:
    c = str(color).strip().lower()
    return floor_rs if ("red" in c or "sparkling" in c) else floor_wr

def compute_row(row: pd.Series) -> pd.Series:
    r = float(row.get("RetailPrice", 0))
    color = str(row.get("Color","")).strip().title()
    is_red = (color == "Red")
    red_bump = RedBump if is_red else 0.0
    force_premium = coerce_bool(row.get("ForcePremium", False))

    bottle = prem_add = prem_mult = None
    if force_premium or r > PremiumMin:
        prem_add  = round(r + PremiumAddOn, 2)          # Premium option A
        prem_mult = round(r * PremiumMult, 2)           # Premium option B
        choice = PremiumChoice.upper()
        bottle = prem_add if choice=="ADDON" else prem_mult if choice=="MULT" else max(prem_add, prem_mult)
    else:
        if r < EntryMax:
            bottle = round(r * (EntryMultiple + red_bump), 2)
        elif r <= MidMax:
            bottle = round(r * (MidMultiple + red_bump), 2)
        else:  # Upper-Mid: MidMax–PremiumMin
            if UM_Method == "ADDON":
                bottle = round(r + UMAddOn, 2)
            else:  # MULT
                bottle = round(r * (UMMultiple + red_bump), 2)

    return pd.Series({"BottlePriceRaw": bottle, "Premium_AddOn": prem_add, "Premium_Mult": prem_mult})

def apply_glass_bounds(color, price_rnd, cap, floor_rs, floor_wr):
    if pd.isna(price_rnd):
        return pd.NA
    floor = color_floor_value(color, floor_rs, floor_wr)
    v = min(float(price_rnd), float(cap))   # cap first
    v = max(v, float(floor))                # then floor
    return int(v)

def needed_glass(bottle_price_rnd, target_multiple, color):
    """Minimum menu-friendly glass (ceil to 5/9) to satisfy 5*glass ≥ target*bottle."""
    if pd.isna(bottle_price_rnd):
        return pd.NA
    raw = (target_multiple * float(bottle_price_rnd)) / 5.0
    base = ceil_to_5_or_9(raw)
    floor = color_floor_value(color, FloorRedSpark, FloorWhiteRose)
    return max(base, floor)

# ---- Input area ----
st.subheader("Input wines")
sample = pd.DataFrame([
    {"Name":"Chianti Classico","Color":"Red","RetailPrice":25,"ForcePremium":False},
    {"Name":"Sancerre","Color":"White","RetailPrice":38,"ForcePremium":False},
    {"Name":"Champagne Brut","Color":"Sparkling","RetailPrice":65,"ForcePremium":False},
    {"Name":"Barolo","Color":"Red","RetailPrice":140,"ForcePremium":False},
])

uploaded = st.file_uploader("Upload CSV with columns: Name, Color, RetailPrice, ForcePremium (optional)", type=["csv"])
df_in = pd.read_csv(uploaded) if uploaded else sample.copy()
df_in = st.data_editor(
    df_in, num_rows="dynamic", use_container_width=True,
    column_config={
        "RetailPrice": st.column_config.NumberColumn("RetailPrice", step=0.01),
        "ForcePremium": st.column_config.CheckboxColumn("ForcePremium"),
        "Color": st.column_config.SelectboxColumn("Color", options=["Red","White","Sparkling","Rosé","Other"])
    }
)
df_in = df_in[df_in.get("Name","").astype(str).str.strip()!=""]  # drop blank names

# ---- Compute & show ----
if not df_in.empty:
    out = pd.concat([df_in, df_in.apply(compute_row, axis=1)], axis=1)

    # raw/rounded bottle + glass
    out["GlassPriceRaw"] = out["BottlePriceRaw"] / GlassServings
    out["BottlePriceRnd"] = out["BottlePriceRaw"].apply(lambda x: pd.NA if pd.isna(x) else round_to_5_or_9(x))
    out["GlassPriceRnd"]  = out["GlassPriceRaw"].apply(lambda x: pd.NA if pd.isna(x) else round_to_5_or_9(x))

   # final glass after cap/floors
out["GlassPrice"] = [
    apply_glass_bounds(c, r, GlassCap, FloorRedSpark, FloorWhiteRose)
    for c, r in zip(out["Color"], out["GlassPriceRnd"])
]

# ----- Menu rounding helper: round UP to the next $..5 or $..9 -----
def menu_round_up(price: float) -> int:
    p = float(price)
    tens = int(p // 10) * 10
    candidates = [tens + 5, tens + 9, tens + 15, tens + 19]  # ends in 5 or 9
    candidates = [c for c in candidates if c >= p]           # keep only >= p
    if not candidates:
        tens += 10
        candidates = [tens + 5, tens + 9]
    return int(min(candidates))

# ----- Diagnostics (BTG worth-it rule) -----
SERVINGS = 5  # 5 glasses per bottle

# Minimum glass price needed to hit 1.20× / 1.25× rule (menu-rounded UP)
out["GlassNeeded120"] = [menu_round_up((1.20 * b) / SERVINGS) for b in out["BottlePriceRnd"]]
out["GlassNeeded125"] = [menu_round_up((1.25 * b) / SERVINGS) for b in out["BottlePriceRnd"]]

out["GlassNeeded125"] = [
    menu_round_up((1.25 * b) / SERVINGS) for b in out["BottlePriceRnd"]
]

# ---- Cap blocking check ----
out["CapBlocks120"] = [g > float(GlassCap) for g in out["GlassNeeded120"]]
out["CapBlocks125"] = [g > float(GlassCap) for g in out["GlassNeeded125"]]

# ---- Actual check: does GlassPrice meet or exceed the needed price? ----
out["GlassRevenueOK120"] = out["GlassPrice"] >= out["GlassNeeded120"]
out["GlassRevenueOK125"] = out["GlassPrice"] >= out["GlassNeeded125"]

# ---- Extra: how many glasses would we need to sell at current GlassPrice? ----
out["GlassesNeededFor120"] = np.ceil(
    (1.20 * out["BottlePriceRnd"]) / out["GlassPrice"]
).astype(int)
out["GlassesNeededFor125"] = np.ceil(
    (1.25 * out["BottlePriceRnd"]) / out["GlassPrice"]
).astype(int)

# ---- Optional: is BTG “worth it”? (can hit target within 5 pours) ----
out["BTG_WorthIt@120"] = out["GlassesNeededFor120"] <= SERVINGS
out["BTG_WorthIt@125"] = out["GlassesNeededFor125"] <= SERVINGS

# ---- Arrow-friendly dtypes ----
for col in ["BottlePriceRnd", "GlassPriceRnd", "GlassPrice", "GlassNeeded120", "GlassNeeded125"]:
    out[col] = out[col].astype("Int64")

# ---- Column ordering ----
cols = [
    "Name", "Color", "RetailPrice", "ForcePremium",
    "BottlePriceRaw", "BottlePriceRnd",
    "GlassPriceRaw", "GlassPriceRnd", "GlassPrice",
    "Premium_AddOn", "Premium_Mult",
    "GlassRevenueOK120", "GlassNeeded120", "CapBlocks120",
    "GlassRevenueOK125", "GlassNeeded125", "CapBlocks125"
]

if not out.empty:
    st.subheader("Results")
    st.dataframe(out[cols], use_container_width=True)

    csv = out[cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download priced CSV", data=csv, file_name="priced_wines.csv", mime="text/csv")
else:
    st.info("Add wines above to see results.")
