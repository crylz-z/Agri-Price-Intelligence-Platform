# 01 Research the context facts

Status: done
Spec: Context text; Sections 1, 2, 7
Blocked by: none

Gather every hand-written fact the page will state, each from a primary or high-trust source, into `.plans/story-v3/sources.md`, so tickets 03 and 06 only copy cited facts. Use the `research` skill.

The facts:
- Hook: whether onions cost more than meat in early 2023, and the source that says so.
- The chain: who traders, wholesalers and stores are in Philippine food supply; what a fair cut pays for (trucking, cold storage, spoilage, market fees).
- Why it matters: farmers' and fisherfolk's poverty incidence (PSA's basic sectors poverty statistics).
- Who got caught: confirm each row of `dbt/seeds/suspects.csv` against its source; note any newer ruling or appeal.
- What can be done: the PCC's cartel enforcement, DA's Kadiwa stores, and where to report overpricing (DTI and DA hotlines or forms), each from the agency's own page.

Done when:
- [x] `sources.md` holds each fact above as one plain sentence with source name, URL and date, or says it couldn't be confirmed.
- [x] Review: the owner reads `sources.md` and strikes any fact they don't trust.

## Notes
- Carried over from the deleted story-rethink plan (session 22): these record sources were blocked for automated fetch and are still unverified: the PTV, PIDS/FFF and FEF pages, the UP/Ateneo paper's findings, Philstar's 7–8 middlemen layers, and Manila Bulletin 2018 on spoilage. A 2019 JESAM Benguet study puts repolyo spoilage at about 42%.
- Leads from that plan: Manila Bulletin 2023-05-17 (Quimbo on the onion cartel) https://mb.com.ph/2023/5/17/quimbo-puts-faces-on-alleged-onion-cartel-as-house-ends-probe; PTV on rice collusion https://ptvnews.ph/lawmakers-lament-collusion-to-manipulate-rice-prices-despite-reduced-tariffs-oversupply/; PIDS on rice traders and the tariff cut https://pids.gov.ph/details/news/in-the-news/rice-traders-capturing-benefits-of-low-tariffs-fff; UP PRE paper https://pre.econ.upd.edu.ph/index.php/pre/article/view/1084; FEF, the other side https://fef.org.ph/?p=9174; Philstar 2024-05 on middlemen layers https://philstar.com/headlines/2024/05/03/2352191/traders-middlemen-blamed-soaring-commodity-prices; Manila Bulletin 2018 on logistics and spoilage https://mb.com.ph/2018/02/15/agricultural-logistics-in-the-philippines; PSA's farm-to-retail report https://psa.gov.ph/system/files/main-publication/AFIS-Prices-and-Marketing_2019-2023_SIGNED.pdf
- 2026-11-20: a background agent wrote `sources.md`, with about 32 facts sourced and 10 not confirmed (each listed under Gaps). psa.gov.ph, dti.gov.ph and the JESAM PDF returned 403, so several facts rest on news pages or search summaries and say so. Recheck the PSA poverty rates, the onion-vs-meat prices and DTI's 1-384 by hand.
- Seed rows for ticket 05 to fix: PCC onion says "announced 15 Oct 2026" (the PCC resolved the case on 28 May), "2019–2023" is unsupported, and the motions for reconsideration are pending, so the fines aren't final. In House onion, the cold-storage claim isn't in BusinessMirror. Rice becomes one lawmaker's "got rich by P13 billion", with no charges filed. Benguet's 42% is the abstract's national figure.
- For ticket 06: DA's program is "KADIWA ng Pangulo", and no DA price-complaint hotline was found. PCC complaints go through ccms.phcc.gov.ph and RA 12022 complaints to the DOJ.
- For ticket 03: no source gives a national split of the middle cut or what a fair cut is. The closest are the BSU Benguet brief (a P44–124/kg margin, 3–8 intermediaries) and a 2012 PIDS paper.
