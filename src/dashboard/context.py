"""The page's hand-written context facts, each with its source (ADR 24).

Data numbers are computed from the marts; these sentences are not, so each
carries a source name, URL and date (`tests/test_context.py` holds that). The
facts and their sources come from `.plans/story-v3/sources.md`, which the owner
checked on 2026-11-20. A date is as precise as the source gives it: "2019-06" or
"2022". `views.cite` shows the source and year after the sentence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fact:
    text: str
    source: str
    url: str
    date: str


# 1. The hook
ONION_VS_MEAT = Fact(
    "At the height of the crisis, onions cost more a kilo than chicken or pork.",
    "AFP via Philstar",
    "https://www.philstar.com/headlines/2023/01/31/2241564/eye-watering-onion-prices-make-philippine-staple-luxury",
    "2023-01-31",
)

# 2. The chain: who each step is
BSU = (
    "Benguet State University",
    "https://bsu.edu.ph/wp-content/uploads/IPP/2022-9-Why-Prices-of-Vegetables-in-"
    "Manila-are-Double-or-Triple-the-Prices-Received-by-Farmers-in-Benguet.pdf",
    "2022",
)
PIDS = (
    "PIDS",
    "https://pidswebs.pids.gov.ph/CDN/PUBLICATIONS/pidsdps1208.pdf",
    "2012-03",
)
FARMER = Fact("Grows the food and sells the harvest to a trader.", *PIDS)
TRADER = Fact(
    "Buys from farmers and links them to the market. Also called a viajero.", *PIDS
)
WHOLESALER = Fact(
    "Packs the harvest, trucks it to city markets and sells it on to stores.", *BSU
)
STORE = Fact("Sells it to you by the kilo.", *BSU)

# 2. What a fair cut pays for
LAYERS = Fact(
    "Vegetables from Benguet pass through 3 to 8 middlemen on the way to Manila, "
    "and each has costs to cover.",
    *BSU,
)
TRUCKING = Fact(
    "Trucking and an allowance for losses are traders' biggest costs.", *PIDS
)
SPOILAGE = Fact(
    "About 42% of vegetable harvests in the Philippines go to waste through spoilage.",
    "JESAM, UPLB",
    "https://ovcre.uplb.edu.ph/journals-uplb/index.php/JESAM/article/download/89/69",
    "2019-06",
)

# 2. Why it matters
POVERTY = Fact(
    "In 2023, 27.0% of farmers and 27.4% of fisherfolk were poor, against 15.5% of "
    "all Filipinos.",
    "PSA via BusinessWorld",
    "https://www.bworldonline.com/?p=663031",
    "2025",
)

# 7. What can be done: what is being done
COMPETITION_ACT = (
    "Philippine Competition Act",
    "https://lawphil.net/statutes/repacts/ra2015/ra_10667_2015.html",
    "2015",
)
PCC_RULING = (
    "Philippine Competition Commission",
    "https://www.phcc.gov.ph/resource-details/pcc-finds-onion-importers-traders-"
    "liable-for-cartel-behavior-slaps-record-fine",
    "2026-10-15",
)
SABOTAGE_ACT = (
    "Anti-Agricultural Economic Sabotage Act",
    "https://lawphil.net/statutes/repacts/ra2024/ra_12022_2024.html",
    "2024-09-26",
)
PCC_POWERS = Fact(
    "The Philippine Competition Commission can investigate price fixing on its "
    "own or on a complaint, and fine a firm up to ₱100 million for a first "
    "offense.",
    *COMPETITION_ACT,
)
PCC_TREBLED = Fact("For a staple food like onions, that fine is tripled.", *PCC_RULING)
SABOTAGE = Fact(
    "Since 2024, hoarding, profiteering and cartels in farm and fish products are "
    "economic sabotage, punished by life in prison.",
    *SABOTAGE_ACT,
)
KADIWA = Fact(
    "The Department of Agriculture's KADIWA ng Pangulo stores sell rice, "
    "vegetables, meat and fish straight from small farmers and fisherfolk, to cut "
    "out the middlemen.",
    "Department of Agriculture",
    "https://www.da.gov.ph/da-phlpost-partner-to-expand-kadiwa-network/",
    "2025-04-04",
)

# 7. What can be done: where to report. The page's report button links here.
PCC_PORTAL = "https://ccms.phcc.gov.ph"
REPORT_PCC = Fact(
    "Report a suspected cartel to the Philippine Competition Commission online at "
    f"[ccms.phcc.gov.ph]({PCC_PORTAL}), or by email at "
    "queries@phcc.gov.ph.",
    "Philippine Competition Commission",
    "https://phcc.gov.ph/enforcement/file-a-complaint",
    "2026-11-20",
)
REPORT_DOJ = Fact(
    "Anyone can file a complaint of hoarding, profiteering or a cartel in farm and "
    "fish products with the Department of Justice.",
    *SABOTAGE_ACT,
)

CHAIN = (
    ("Farmer", "agriculture", FARMER),
    ("Trader", "local_shipping", TRADER),
    ("Wholesaler", "warehouse", WHOLESALER),
    ("Store", "storefront", STORE),
)
FAIR_CUT = (LAYERS, TRUCKING, SPOILAGE)
# Each card in "Being done": title, Material icon, fact.
BEING_DONE = (
    ("Fines for cartels", "gavel", PCC_POWERS),
    ("Triple for staples", "priority_high", PCC_TREBLED),
    ("Life in prison", "lock", SABOTAGE),
    ("Farm-direct stores", "storefront", KADIWA),
)
REPORT = (REPORT_PCC, REPORT_DOJ)


def facts() -> list[Fact]:
    """Every fact in this module, so a test can check each one's source."""
    return [v for v in globals().values() if isinstance(v, Fact)]
