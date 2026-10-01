"""
Estimation for the 2026-09 revision.

Primary comparison  : four provider groups, reference = public hospital OPD/ER.
Primary inference   : logistic regression, cluster-robust (subdistrict) covariance.
Reported quantities : aOR with 95% CI *and* average marginal predicted probabilities
                      with percentage-point differences, because an odds ratio is not
                      a probability ratio.
Multiplicity        : Benjamini-Hochberg within each pre-declared outcome family.
"""
from __future__ import annotations
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from . import preparation as prep

REF = 'public hospital OPD/ER'
GRP_ORDER = [REF] + [g for g in prep.GROUPS if g != REF]

# Conceptual covariate set: demographics, geography, socioeconomic position,
# coverage, and need. Declared once and used for every adjusted model.
COVARIATES = ['age_cat4', 'sex', 'edu_gr', 'income3', 'municipality', 'scheme_gr',
              'health_good3', 'chronic']
COV_FORMULA = (' + C(age_cat4, Treatment(reference="30-49"))'
               ' + C(sex, Treatment(reference="male"))'
               ' + C(edu_gr, Treatment(reference="lower secondary or below"))'
               ' + C(income3, Treatment(reference="<10k"))'
               ' + C(municipality, Treatment(reference="non-municipal"))'
               ' + C(scheme_gr, Treatment(reference="UCS"))'
               ' + C(health_good3, Treatment(reference="fair or poor"))'
               ' + C(chronic, Treatment(reference="no"))')


# ------------------------------------------------------------------ helpers
def bh(pvals):
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(pvals, dtype=float)
    ok = ~np.isnan(p)
    out = np.full(p.shape, np.nan)
    q = p[ok]
    n = len(q)
    if n == 0:
        return out
    order = np.argsort(q)
    ranked = q[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty(n)
    adj[order] = np.clip(ranked, 0, 1)
    out[ok] = adj
    return out


def prop_ci(k, n):
    """Wilson 95% interval."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    z = 1.959964
    d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    h = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return (100*p, 100*max(0, c-h), 100*min(1, c+h))


def describe_binary(df, var, positive, group='provider_group', groups=None):
    """n/N, %, Wilson CI per group + chi-square across groups."""
    groups = groups or prep.GROUPS
    sub = df[[var, group]].dropna()
    rows = {}
    for g in groups:
        s = sub.loc[sub[group] == g, var]
        k, n = int((s == positive).sum()), len(s)
        p, lo, hi = prop_ci(k, n)
        rows[g] = dict(k=k, n=n, pct=p, lo=lo, hi=hi,
                       fmt=f'{k}/{n} ({p:.1f}; {lo:.1f}-{hi:.1f})' if n else '--')
    ct = pd.crosstab(sub[var], sub[group]).reindex(columns=groups).fillna(0)
    try:
        chi2, p, dof, _ = stats.chi2_contingency(ct)
        expected = stats.chi2_contingency(ct)[3]
        sparse = bool((expected < 5).any())
    except Exception:
        p, sparse = np.nan, True
    return rows, p, sparse


# ------------------------------------------------------------------ modelling
def fit_group_model(df, outcome, positive, extra_terms='', cluster='subdist',
                    covariates=COV_FORMULA, ref=REF):
    """
    Logistic model of `outcome == positive` on provider group + covariates.
    Returns (result, analytic frame, events table) or (None, reason, None).
    """
    need = [outcome, 'provider_group', cluster] + COVARIATES
    dd = df.dropna(subset=[c for c in need if c in df.columns]).copy()
    if len(dd) == 0:
        return None, 'no complete cases', None
    dd['y'] = (dd[outcome] == positive).astype(int)
    dd['grp'] = pd.Categorical(dd['provider_group'].astype('object'),
                               categories=[ref] + [g for g in prep.GROUPS if g != ref])
    ev = dd.groupby('grp', observed=True)['y'].agg(['sum', 'count'])
    ev.columns = ['events', 'n']
    # refuse to estimate where a cell is empty (separation) rather than force a number
    if (ev['events'] == 0).any() or (ev['events'] == ev['n']).any():
        return None, 'not estimable (zero or complete cell)', ev
    f = f'y ~ C(grp, Treatment(reference="{ref}")){covariates}{extra_terms}'
    groups = dd[cluster].astype('category').cat.codes
    try:
        model = smf.logit(f, data=dd)
        m = model.fit(disp=0, maxiter=200)                       # model-based, for predict()
        if not m.mle_retvals.get('converged', True):
            return None, 'did not converge (quasi-separation or sparse cells)', ev
        # Cluster-robust on the PPS-selected subdistricts. Final within-subdistrict
        # selection was quota-based convenience, so this is an approximate
        # cluster-adjusted variance, not a design-based one (see supplement §A).
        mc = model.fit(disp=0, maxiter=200, cov_type='cluster',
                       cov_kwds={'groups': groups})
    except Exception as e:
        return None, f'failed: {type(e).__name__}: {e}', ev
    return (m, mc, dd, ev), None, ev


def group_contrasts(fitted, outcome_label):
    """aOR + CI (cluster-robust) and average marginal predicted probabilities."""
    m, mc, dd, ev = fitted
    names = list(m.params.index)
    rows = []
    # --- average marginal predicted probability per group (G-computation)
    preds = {}
    for g in GRP_ORDER:
        tmp = dd.copy()
        tmp['grp'] = pd.Categorical([g]*len(tmp), categories=GRP_ORDER)
        preds[g] = float(m.predict(tmp).mean())
    for i, nm in enumerate(names):
        if not nm.startswith('C(grp'):
            continue
        g = nm.split('T.')[1].rstrip(']')
        b, se = float(np.asarray(mc.params)[i]), float(np.asarray(mc.bse)[i])
        lo, hi = b - 1.959964*se, b + 1.959964*se
        rows.append({'Outcome': outcome_label, 'Group': g, 'Reference': REF,
                     'aOR': np.exp(b), 'lo': np.exp(lo), 'hi': np.exp(hi),
                     'p': float(np.asarray(mc.pvalues)[i]),
                     'Pred. prob. (%)': 100*preds[g],
                     'Pred. prob. ref (%)': 100*preds[REF],
                     'Diff (pp)': 100*(preds[g] - preds[REF]),
                     'n': int(m.nobs),
                     'events': int(ev.loc[g, 'events']), 'group n': int(ev.loc[g, 'n'])})
    return rows


def omnibus(fitted):
    """Wald test that all three provider-group coefficients are jointly zero."""
    m, mc, dd, ev = fitted
    idx = [i for i, nm in enumerate(m.params.index) if nm.startswith('C(grp')]
    if not idx:
        return np.nan
    R = np.zeros((len(idx), len(m.params)))
    for r, i in enumerate(idx):
        R[r, i] = 1
    try:
        return float(mc.wald_test(R, scalar=True).pvalue)
    except Exception:
        try:
            return float(mc.wald_test(R).pvalue)
        except Exception:
            return np.nan


# Reduced specification used only when the full model cannot be estimated
# (near-universal outcome / sparse cells). Reported as such, never silently.
COV_FORMULA_SIMPLE = (' + C(age_cat4, Treatment(reference="30-49"))'
                      ' + C(sex, Treatment(reference="male"))'
                      ' + C(municipality, Treatment(reference="non-municipal"))')


COV_FORMULA_NO_SEX = COV_FORMULA.replace(
    ' + C(sex, Treatment(reference="male"))', '')


def run_family(df, spec, family_name, extra_terms='', allow_simplified=True,
               restrict=None, covariates=COV_FORMULA):
    """
    spec: list of (outcome_col, positive_value, label).
    restrict: optional dict {outcome_col: boolean mask} applying a survey-eligible
              denominator (e.g. sex-restricted screening items).
    """
    est, notes = [], []
    for col, pos, lab in spec:
        sub = df if not restrict or col not in restrict else df[restrict[col]]
        fitted, err, ev = fit_group_model(sub, col, pos, extra_terms=extra_terms,
                                          covariates=covariates)
        if err and allow_simplified and 'converge' in err:
            fitted2, err2, ev2 = fit_group_model(sub, col, pos, extra_terms=extra_terms,
                                                 covariates=COV_FORMULA_SIMPLE)
            if not err2:
                rows = group_contrasts(fitted2, lab)
                om = omnibus(fitted2)
                for r in rows:
                    r['Family'] = family_name
                    r['Omnibus p (group)'] = om
                    r['Specification'] = 'SIMPLIFIED (age, sex, municipality only)'
                est += rows
                notes.append({'Family': family_name, 'Outcome': lab,
                              'Status': 'full model ' + err + '; simplified model reported',
                              'Detail': '; '.join(f'{g}: {int(r.events)}/{int(r.n)}'
                                                  for g, r in ev.iterrows())})
                continue
        if err:
            notes.append({'Family': family_name, 'Outcome': lab, 'Status': err,
                          'Detail': '' if ev is None else
                          '; '.join(f'{g}: {int(r.events)}/{int(r.n)}' for g, r in ev.iterrows())})
            continue
        rows = group_contrasts(fitted, lab)
        om = omnibus(fitted)
        for r in rows:
            r['Family'] = family_name
            r['Omnibus p (group)'] = om
            r['Specification'] = ('Full (age, education, income, municipality, scheme, '
                                  'self-rated health, chronic illness'
                                  + (', sex)' if 'sex' in covariates else '; sex not applicable)'))
        est += rows
    E = pd.DataFrame(est)
    if len(E):
        E['p (BH within family)'] = bh(E['p'].values)
    return E, pd.DataFrame(notes)
