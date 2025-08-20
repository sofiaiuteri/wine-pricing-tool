import os
import pandas as pd
from tabulate import tabulate

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
csv_path = os.path.join(BASE_DIR, "data", "wines.csv")
out_path = os.path.join(BASE_DIR, "data", "priced_wines.csv")

# === RULES ===
ENTRY_MAX = 50.0          # retail < 50
MID_MIN, MID_MAX = 50.0, 80.0
PREMIUM_MIN = 120.0
PREMIUM_CHOICE = "HIGHER"   # options: "ADDON", "MULT", "HIGHER"
GLASS_SERVINGS = 5           # ~25 oz bottle / 5 oz pour
ROUND_TO_5 = True            # round prices to nearest $5

ENTRY_MULTIPLE = 2.40
MID_MULTIPLE = 2.10
RED_BUMP = 0.10           # add to entry/mid multiples if red

PREMIUM_ADDON = 100.0     # option A
PREMIUM_MULT = 1.50       # option B

def compute_prices(row):
    r = float(row["RetailPrice"])
    color = str(row.get("Color","")).strip().title()
    red_bump = RED_BUMP if color == "Red" else 0.0

    bottle, prem_add, prem_mult = None, None, None

    if r > PREMIUM_MIN or str(row["ForcePremium"]).strip().upper() == "TRUE":
        prem_add  = round(r + PREMIUM_ADDON, 2)     # option A
        prem_mult = round(r * PREMIUM_MULT, 2)      # option B

        choice = PREMIUM_CHOICE.upper()             # what shows in BottlePrice
        if choice == "ADDON":
            bottle = prem_add
        elif choice == "MULT":
            bottle = prem_mult
        else:  # HIGHER
            bottle = max(prem_add, prem_mult)

    elif r < ENTRY_MAX:
        bottle = round(r * (ENTRY_MULTIPLE + red_bump), 2)
    elif MID_MIN <= r <= MID_MAX:
        bottle = round(r * (MID_MULTIPLE + red_bump), 2)
    else:  # between 80 and 120
        bottle = round(r * (MID_MULTIPLE + red_bump), 2)

    return pd.Series({
        "BottlePrice": bottle,
        "Premium_AddOn": prem_add,
        "Premium_Mult": prem_mult
    })

import math

def round_to_5_or_9(x):
    x = float(x)
    # nearest multiple of 5 (force half-up)
    nearest5 = 5 * math.floor(x/5 + 0.5)
    # nearest ending in 9
    nearest9 = 10 * math.floor((x-9)/10 + 0.5) + 9
    # choose whichever is closer
    if abs(x - nearest5) <= abs(x - nearest9):
        return nearest5
    else:
        return nearest9

df = pd.read_csv(csv_path)
df = pd.read_csv(csv_path)
df = pd.concat([df, df.apply(compute_prices, axis=1)], axis=1)

# RAW values
df["BottlePriceRaw"] = df["BottlePrice"]
df["GlassPriceRaw"]  = df["BottlePriceRaw"] / GLASS_SERVINGS

# ROUNDED values (nearest …5 or …9)
df["BottlePriceRnd"] = df["BottlePriceRaw"].apply(round_to_5_or_9)
df["GlassPriceRnd"]  = df["GlassPriceRaw"].apply(round_to_5_or_9)

# Tidy output (RAW + ROUNDED visible)
df_out = df[[
    "Name","Color","RetailPrice","ForcePremium",
    "BottlePriceRaw","BottlePriceRnd",
    "GlassPriceRaw","GlassPriceRnd",
    "Premium_AddOn","Premium_Mult"
]].fillna("")

from tabulate import tabulate
print(tabulate(df_out, headers="keys", tablefmt="github", showindex=False))

out_path = os.path.join(BASE_DIR, "data", "priced_wines.csv")
df_out.to_csv(out_path, index=False)
print(f"\nSaved to {out_path}")