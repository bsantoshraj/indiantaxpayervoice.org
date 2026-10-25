# 12. The ₹2 lakh cap on house-property losses: what changed in 2017, and who it hit

**Since 2018-19, the interest on a home loan can cut your other taxable income by at most ₹2 lakh a year. For the home you live in, that limit already existed. The 2017 change hit people who borrowed to buy a home they rent out. Under the new tax regime, that loss counts for nothing at all.**

### What the law says

| Situation | Old regime | New regime |
| --- | --- | --- |
| Interest on a loan for the home you live in | Deduction up to ₹2,00,000 a year \[2\] | No deduction \[2\] |
| Let-out home: loss (interest more than rent) set against salary or other income, **before AY 2018-19** | No limit \[1\]\[3\] | (no new regime then) |
| Let-out home: the same loss, **from AY 2018-19** | Up to ₹2,00,000 a year; the rest carried forward for up to 8 years, usable only against future income from house property \[1\]\[2\] | Not allowed, and not carried forward \[2\] |

The change came from the Finance Act 2017, which inserted section 71(3A) into the Income-tax Act from 1 April 2018. It says the taxpayer "shall not be entitled to set off such loss, to the extent the amount of the loss exceeds two lakh rupees, against income under the other head" \[1\].

### How many people report a house-property loss

CBDT's return statistics show the number of individuals whose income from house property was negative, before any set-off \[4\]\[5\]:

| Assessment year | Individuals with a house-property loss | Total loss | Average loss |
| --- | --- | --- | --- |
| AY 2022-23 | 53,20,848 | ₹64,071.91 crore | ₹1.20 lakh |
| AY 2023-24 | 59,69,685 | ₹77,808.70 crore | ₹1.30 lakh |

The tables do not show how many of these losses were above ₹2 lakh, so the number of people the cap actually affects, and the tax it raises, are not in this data.

### A worked example (our calculation)

A salaried person in the 30% slab buys a flat to rent out with a ₹94 lakh loan at 8.5% over 20 years: an EMI of ₹81,575 a month, of which about ₹8 lakh in the first year is interest. The flat earns ₹3 lakh a year in rent. After the 30% standard deduction on rent (₹90,000) \[1\] and the interest, the result from house property is a loss of ₹5,90,000.

|  | Before AY 2018-19 | From AY 2018-19, old regime | New regime |
| --- | --- | --- | --- |
| Loss set against salary | ₹5,90,000 | ₹2,00,000 | ₹0 |
| Tax saved (30% + 4% cess) | ₹1,84,080 | ₹62,400 | ₹0 |
| Loss carried forward | None needed | ₹3,90,000 | None |

The carried-forward loss helps only if the flat later earns more than its interest. While the loan is large and rent is low, it usually expires unused after eight years.

### A long loan taken before 2017 (our calculation)

A longer loan makes the effect starker: on a 30-year loan the interest barely falls in the first decade, so the cap bites every year. An illustration, with assumed numbers:

Say a flat was bought to let out in April 2016 with a 30-year loan of about ₹1.95 crore at 8.5%: an EMI of ₹1.5 lakh a month, ₹18 lakh a year. The rent is ₹25,000 a month, and the owner is in the 30% slab under the old regime.

| Year | Interest | Loss from the flat | Set off against salary | Carried forward | Extra tax vs old rules |
| --- | --- | --- | --- | --- | --- |
| 2016-17 | ₹16.53 lakh | ₹14.43 lakh | ₹14.43 lakh | — | — |
| 2017-18 | ₹16.39 lakh | ₹14.29 lakh | ₹2 lakh | ₹12.29 lakh | ₹3.84 lakh |
| 2019-20 | ₹16.10 lakh | ₹14.00 lakh | ₹2 lakh | ₹12.00 lakh | ₹3.74 lakh |
| 2021-22 | ₹15.75 lakh | ₹13.65 lakh | ₹2 lakh | ₹11.65 lakh | ₹3.63 lakh |
| 2023-24 | ₹15.33 lakh | ₹13.23 lakh | ₹2 lakh | ₹11.23 lakh | ₹3.50 lakh |
| 2025-26 | ₹14.84 lakh | ₹12.74 lakh | ₹2 lakh | ₹10.74 lakh | ₹3.35 lakh |

Ten years in, interest is still ₹14.8 lakh of the ₹18 lakh EMI, only 10% below the first year. From 2017-18 the tax relief is frozen at ₹62,400 a year, while about ₹11–12 lakh of loss a year is carried forward: ₹1.04 crore over nine years. It can only be set against future income from the flat, which never arrives while rent is below interest, so each year's loss lapses after eight years. Compared with the rules the loan was taken under, the owner pays about ₹32.6 lakh more tax over those nine years. Under the new regime the relief is zero.

All years are in `research/data/a12-long-loan.csv`; the calculation is `research/scripts/article12_long_loan.py`. It assumes a fixed rate, no municipal tax and no surcharge; it is an illustration, not tax advice.

### Is it abuse?

**The case against the cap.** Renting out a home is earning income, and interest is the cost of earning it. Every business deducts its costs before paying tax on profit. On that view, taxing someone on their salary while ignoring a real loss on their rental is taxing gross earnings, not net income. And the ₹2 lakh limit is a fixed rupee amount, not linked to inflation or to loan sizes.

**The government's case.** In court, the government said that before 2017 there was no upper limit except for self-occupied homes, which led to "escalation of property prices and reduction in supply of affordable housing" and to lost revenue as "the higher income group reduced its tax liability" through large interest payments. It called the cap "an anti-abuse provision" and "not a revenue raising measure" \[1\]. The 2017 Budget papers described it as "in line with the international best practices" \[3\].

**What the court decided.** In *Sanjeev Goyal v. Union of India*, the Delhi High Court on 30 May 2024 dismissed a challenge from a taxpayer whose loan dated from before 2017. It held the cap was not retrospective, took away no vested right, and did not breach Articles 14 or 19(1)(g), adding that the legislature "has been guided by verifiable data" \[1\]. The judgment does not reproduce that data, and we have not found it published.

**Existing borrowers.** The cap applied from AY 2018-19 to every loan, including those taken years earlier by people who had planned their EMIs around the full set-off. The court held that this is not retrospective in law, because nobody has a vested right to future tax treatment \[1\]. But protecting existing positions is a choice governments make: a year later, the Finance Act 2018 taxed long-term gains on listed shares and equity funds while keeping gains made up to 31 January 2018 outside the new tax \[6\]. Borrowers in 2017 got no such protection. Whether they should have, for example by capping only loans taken after 1 April 2017, or by treating one rented-out home differently from several, is a policy question the court was not asked to decide.

**Worth knowing.** The law already keeps salary apart from other losses: a loss from a business or profession cannot be set against salary at all (section 71(2A)) \[1\]. Under the old regime, a house-property loss is treated more generously than that, up to ₹2 lakh. Under the new regime, the two are treated the same: nothing.

> Owner check: the example is our calculation; have a tax professional check it. The number of taxpayers whose loss exceeds ₹2 lakh, and the tax the cap raises, are good questions for an RTI application to CBDT. General information, not tax advice.

**LinkedIn**

> Bought a flat on a loan and rented it out? Since 2018-19, only ₹2 lakh of the loss can reduce the tax on your salary, however large the interest. Under the new regime, none of it can.
>
> In our example, a ₹94 lakh loan and ₹3 lakh rent: tax relief fell from ₹1.84 lakh a year to ₹62,400, and to zero under the new regime.
>
> The government calls the cap anti-abuse; the Delhi High Court upheld it in 2024. Existing borrowers got no protection, though a year later Budget 2018 protected gains already made on shares. Nearly 60 lakh people reported a house-property loss in AY 2023-24 (CBDT).
>
> Should the costs of earning income count before tax? Tell us anonymously in 5 minutes: https://indiantaxpayervoice.org/participate/?utm\_source=linkedin&utm\_medium=social&utm\_campaign=articles
>
> Sources: Finance Act 2017 s.71(3A); Delhi High Court, Sanjeev Goyal v. UOI (2024); CBDT return statistics.

**X**

> Rented-out flat on a home loan? Since 2018-19, only ₹2L of the loss counts against your salary; under the new regime, ₹0. Govt calls it anti-abuse; Delhi HC upheld it in 2024. Should costs come before tax? Anonymous survey: https://indiantaxpayervoice.org/participate/?utm\_source=x&utm\_medium=social&utm\_campaign=articles

**WhatsApp / Facebook**

> Paying a home-loan EMI on a flat you rent out? Since 2018-19, only ₹2 lakh of the loss can reduce the tax on your salary, and under the new tax regime nothing can. Nearly 60 lakh people reported such a loss in AY 2023-24. Tell us what you think, anonymously, in 5 minutes: https://indiantaxpayervoice.org/participate/?utm\_source=whatsapp&utm\_medium=share&utm\_campaign=articles

### References

1. Delhi High Court. *Sanjeev Goyal v. Union of India*, W.P.(C) 10214/2017, judgment of 30 May 2024 (quotes sections 24, 71 and Finance Act 2017 section 31, and the government's stated rationale). https://livelaw.in/pdf\_upload/59630052024cw102142017165324-542742.pdf Evidence: `research/sources/a12-delhihc-sanjeev-goyal-2024.pdf`, SHA-256 edb7e166f3bdb4dd…
2. Income Tax Department, Government of India. *Salaried Individuals for AY 2026-27* (house property deductions under the old and new regimes). https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 (accessed 24 Oct 2026). Evidence: `research/sources/a07-itd-salaried-ay2026-27.html`, SHA-256 c394823582f2d8dc…
3. Business Today / PTI. *Union Budget restricts tax benefit on second house to Rs 2 lakh*. 2 Feb 2017. https://www.businesstoday.in/business/news/story/union-budget-restricts-tax-benefit-on-second-house-to-rs-2-lakh-72676-2017-02-02 (evidence: local copy, SHA-256 78fb15a4c13a1fb1…)
4. Central Board of Direct Taxes. *Income Tax Return Statistics, Assessment Year 2022-23*, table 2.3 (individuals, range of house property income). https://incometaxindia.gov.in/Documents/Direct%20Tax%20Data/Approved-version-Income-Tax-Return-Statistics-for-the-AY-2022-23-14062024.pdf Evidence: `research/sources/a11-cbdt-itr-stats-ay2022-23.pdf`, SHA-256 31dfd5c2185ecd0f…
5. Central Board of Direct Taxes. *Income Tax Return Statistics, Assessment Year 2023-24*, table 2.3. Evidence: `research/sources/a11-cbdt-itr-stats-ay2023-24.pdf`, SHA-256 eeb7c53d4cd62a71…; extracted by `research/scripts/cbdt_tables.py` to `research/data/cbdt-ay2023-24-individual-house-property-income.csv`
6. Antal S. K. *Grandfathering provisions: capital gains*. TaxGuru, 7 Nov 2021 (cost of listed shares and equity fund units bought before 1 February 2018 stepped up to their 31 January 2018 value). https://taxguru.in/income-tax/grandfathering-provisions-capital-gains.html (evidence: local copy, SHA-256 4fae168257a2af8d…)

