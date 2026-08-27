import numpy as np

# ---- WACC build ----
rf = 0.045          # VN 10Y govt bond yield, ~4.3-4.5% (Aug 2026, web cross-check)
erp = 0.08           # VN frontier-market ERP (7-9% per framework; base=8%)
beta_adj = 0.729     # 2Y weekly regression FPT vs VNINDEX, Bloomberg-adjusted (raw 0.593)
company_risk_premium = 0.010  # idiosyncratic add-on: FPT Telecom deconsolidation / governance-control uncertainty (state security ministry now controlling shareholder), cash-upstream risk from associate
ke = rf + beta_adj*erp + company_risk_premium

kd_pretax = 0.065    # blended assumption: trailing eff. cost of debt avg ~4.3-6.3%, current rate env higher
tax_eff = 0.15       # FPT effective tax rate ~14-16% (software/IT tax incentives), FY25=13.9%
kd_post = kd_pretax*(1-tax_eff)

mktcap = 72400 * 1_714_326_422  # today's close x current listed shares
total_debt_2026q2 = 16_368.92e9 + 2_080.611e9
d_weight = total_debt_2026q2 / (total_debt_2026q2 + mktcap)
e_weight = 1 - d_weight
wacc = e_weight*ke + d_weight*kd_post

print(f"Ke = {ke:.4%}")
print(f"Kd (post-tax) = {kd_post:.4%}")
print(f"Market cap = {mktcap/1e9:,.0f} bn VND")
print(f"Total debt (2026Q2) = {total_debt_2026q2/1e9:,.0f} bn VND")
print(f"E weight = {e_weight:.2%}, D weight = {d_weight:.2%}")
print(f"WACC (base) = {wacc:.4%}")

def run_dcf(wacc, g_terminal, rev_growth, ebitda_margin_path, da_pct=0.032, capex_pct=0.05, nwc_pct_drev=0.03,
            rev0=58580e9, tax=0.15):
    years = len(rev_growth)
    rev = [rev0]
    for g in rev_growth:
        rev.append(rev[-1]*(1+g))
    rev = rev[1:]  # 5 forecast years, rev[0] = year1 = rev0 itself already (rev_growth[0] should be 0 for year1 anchor)
    fcffs = []
    prior_rev = rev0/(1+rev_growth[0])  # base year revenue proxy for NWC delta in year1 (approx)
    prev_rev = rev0 / (1+rev_growth[0])
    for i, r in enumerate(rev):
        ebitda = r*ebitda_margin_path[i]
        da = r*da_pct
        ebit = ebitda - da
        nopat = ebit*(1-tax)
        capex = r*capex_pct
        d_rev = r - (rev[i-1] if i>0 else prev_rev)
        d_nwc = d_rev*nwc_pct_drev
        fcff = nopat + da - capex - d_nwc
        fcffs.append(fcff)
    # terminal value (Gordon growth) on final year FCFF
    tv = fcffs[-1]*(1+g_terminal) / (wacc - g_terminal)
    disc = [(1+wacc)**(i+1) for i in range(years)]
    pv_fcff = sum(f/d for f,d in zip(fcffs, disc))
    pv_tv = tv/disc[-1]
    ev = pv_fcff + pv_tv
    return ev, fcffs, tv, rev

# ---- Base case: conservative, margin held flat (not yet proven durable), faster taper ----
rev_growth_base = [0.00, 0.13, 0.10, 0.08, 0.06]   # yr1 anchor=guidance level(0%), yr2-5 growth off guided base
ebitda_margin_base = [0.246, 0.246, 0.248, 0.250, 0.250]
ev_base, fcff_base, tv_base, rev_base = run_dcf(wacc, 0.04, rev_growth_base, ebitda_margin_base, capex_pct=0.05)

# ---- Bull: margin expansion thesis plays out, AI-First growth sustained ----
rev_growth_bull = [0.00, 0.17, 0.14, 0.11, 0.09]
ebitda_margin_bull = [0.252, 0.258, 0.263, 0.267, 0.270]
ev_bull, fcff_bull, tv_bull, rev_bull = run_dcf(wacc-0.01, 0.05, rev_growth_bull, ebitda_margin_bull, capex_pct=0.045)

# ---- Bear: capex stays elevated (AI infra), margin compresses back toward telecom-era average, growth slows ----
rev_growth_bear = [0.00, 0.08, 0.06, 0.05, 0.04]
ebitda_margin_bear = [0.230, 0.225, 0.222, 0.220, 0.220]
ev_bear, fcff_bear, tv_bear, rev_bear = run_dcf(wacc+0.015, 0.035, rev_growth_bear, ebitda_margin_bear, capex_pct=0.06)

print("\n=== Revenue path (base) bn VND ===", [round(x/1e9) for x in rev_base])
print("=== FCFF path (base) bn VND ===", [round(x/1e9) for x in fcff_base])
print(f"EV base = {ev_base/1e9:,.0f} bn; TV(undisc) base = {tv_base/1e9:,.0f} bn, TV%EV = {(tv_base/(1+wacc)**5)/ev_base:.1%}")
print(f"EV bull = {ev_bull/1e9:,.0f} bn")
print(f"EV bear = {ev_bear/1e9:,.0f} bn")

# ---- EV -> equity bridge ----
cash_2026q2 = 5_829.076e9 + 3_014.085e9
st_inv_2026q2 = 20_128.42e9
minority_2026q2 = 1_144.217e9
shares = 1_714_326_422

def ev_to_price(ev, include_st_inv=False):
    cash = cash_2026q2 + (st_inv_2026q2 if include_st_inv else 0)
    equity_val = ev - total_debt_2026q2 + cash - minority_2026q2
    return equity_val, equity_val/shares

eq_base, px_base = ev_to_price(ev_base, include_st_inv=False)
eq_base_b, px_base_b = ev_to_price(ev_base, include_st_inv=True)
eq_bull, px_bull = ev_to_price(ev_bull, include_st_inv=False)
eq_bear, px_bear = ev_to_price(ev_bear, include_st_inv=False)

print(f"\nBase case (strict cash) equity value = {eq_base/1e9:,.0f} bn -> price/share = {px_base:,.0f} VND")
print(f"Base case (cash+ST investments) equity value = {eq_base_b/1e9:,.0f} bn -> price/share = {px_base_b:,.0f} VND")
print(f"Bull case price/share = {px_bull:,.0f} VND")
print(f"Bear case price/share = {px_bear:,.0f} VND")
print(f"Current price = 72,400 VND")
print(f"Upside/downside base(strict) = {px_base/72400-1:.1%}")
print(f"Upside/downside base(cash+STinv) = {px_base_b/72400-1:.1%}")
print(f"Upside bull = {px_bull/72400-1:.1%}")
print(f"Downside bear = {px_bear/72400-1:.1%}")

# ---- WACC / g sensitivity table (base case cashflows, strict cash) ----
print("\n=== Sensitivity: price/share by WACC x terminal g (base FCFF path, strict cash) ===")
waccs = [wacc-0.01, wacc-0.005, wacc, wacc+0.005, wacc+0.01]
gs = [0.04, 0.045, 0.05, 0.055, 0.06]
header = "WACC\\g  " + "  ".join(f"{g:.1%}" for g in gs)
print(header)
for w in waccs:
    row = [f"{w:.2%}"]
    for g in gs:
        ev_s, _, _, _ = run_dcf(w, g, rev_growth_base, ebitda_margin_base)
        _, p = ev_to_price(ev_s, include_st_inv=False)
        row.append(f"{p:,.0f}")
    print("  ".join(row))
