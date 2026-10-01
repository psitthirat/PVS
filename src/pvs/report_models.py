"""Re-estimate the October report's overall models from the canonical frame.

These are the report's original complete-case, model-based logistic models,
not the September four-provider, cluster-adjusted models. Exact-age bands and
the original exclusions are retained. Physical health uses good or better;
breast/cervical screening models include women only, without a sex term.
Only aggregate coefficients and diagnostics are returned.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


REFERENCES = {
    'sex': 'male', 'area': 'non-municipal', 'education': 'primary or lower',
    'age': 'under 30', 'income': 'low', 'scheme': 'UCS', 'activation': 'low',
    'health': 'fair or poor', 'usual': 'no', 'sector': 'private',
    'setting': 'hospital',
}
BASE = ['sex', 'area', 'education', 'age', 'income', 'scheme', 'activation', 'health']


def term(variable):
    return f'C({variable}, Treatment(reference="{REFERENCES[variable]}"))'


def estimate(raw):
    d = pd.DataFrame(index=raw.index)
    for target, source in {
        'sex': 'sex', 'area': 'municipality', 'scheme': 'scheme',
        'activation': 'activation', 'health': 'health_good3',
        'usual': 'has_usual', 'sector': 'usual_sector',
        'quality': 'usual_qual_top2', 'security': 'health_security',
        'improved': 'sys_improved_bin', 'works': 'sys_endorse_bin',
    }.items():
        d[target] = raw[source].astype(object)
    d['activation'] = d.activation.replace({'not high': 'low'})
    d['education'] = raw.edu.astype(object).map({
        'below primary': 'primary or lower', 'primary': 'primary or lower',
        'lower secondary': 'secondary or higher', 'upper secondary/voc': 'secondary or higher',
        'diploma/high voc': 'secondary or higher', 'bachelor or above': 'secondary or higher',
    })
    d['income'] = raw.income.astype(object).map({
        '<10k': 'low', '10-30k': 'low', '30-60k': 'middle', '60-100k': 'high', '100k+': 'high',
    })
    d['age'] = pd.cut(raw.age_exact, [0, 30, 45, 60, 75, 105], right=False,
                      labels=['under 30', '30-44', '45-59', '60-74', '75+']).astype(object)
    d['setting'] = raw.usual_hospital.map({True: 'hospital', False: 'nonhospital'})
    for variable in ['bp', 'sugar', 'lipid', 'mammogram', 'ca_cervix', 'vision', 'dental']:
        d[variable] = raw[variable + '_r'].astype(object)
    # Match the stated historical inclusion rule, retaining people with no usual
    # source in the usual-source models, but excluding unclassifiable settings.
    eligible = (d.sex.isin(['male', 'female']) & d.scheme.isin(['UCS', 'SSS', 'CSMBS'])
                & ~d.sector.isin(['non-profit', 'other'])
                & ~raw.fhos_type.astype('string').str.startswith('7.', na=False))
    d = d.loc[eligible].copy()

    def fit(outcome, positive, predictors, *, women=False, univariate=False):
        subset = d.loc[d.sex.eq('female')] if women else d
        subset = subset[[outcome, *predictors]].dropna().copy()
        subset['y'] = subset[outcome].eq(positive).astype(int)
        result = {'n': len(subset), 'events': int(subset.y.sum()),
                  'covariance': 'nonrobust (model-based)', 'predictors': predictors,
                  'women_only': women, 'multivariate': [], 'univariate': []}

        def fitted(variables):
            formula = 'y ~ ' + ' + '.join(term(v) for v in variables)
            model = smf.logit(formula, subset).fit(disp=0, maxiter=200)
            if not model.mle_retvals.get('converged') or not np.isfinite(model.bse).all():
                raise ValueError(f'Model failed to converge: {outcome}')
            ci = np.exp(model.conf_int())
            rows = []
            for name in model.params.index:
                if name == 'Intercept':
                    continue
                variable = next(v for v in variables if name.startswith('C(' + v + ','))
                rows.append({'variable': variable, 'level': name.split('[T.', 1)[1][:-1],
                             'reference': REFERENCES[variable], 'aOR': float(np.exp(model.params[name])),
                             'lo': float(ci.loc[name, 0]), 'hi': float(ci.loc[name, 1]),
                             'p': float(model.pvalues[name])})
            return rows

        result['multivariate'] = fitted(predictors)
        if univariate:
            result['univariate'] = [row for v in predictors for row in fitted([v])]
        return result

    out = {'T08': fit('quality', 'very good/excellent', BASE + ['sector', 'setting'], univariate=True)}
    out['T09'] = {}
    for variable in ['bp', 'sugar', 'lipid', 'mammogram', 'ca_cervix', 'vision', 'dental']:
        women = variable in ['mammogram', 'ca_cervix']
        predictors = [p for p in BASE if not (women and p == 'sex')] + ['usual']
        out['T09'][variable] = fit(variable, 'yes', predictors, women=women)
    for table, variable in [('T11', 'usual'), ('T12', 'sector')]:
        out[table] = {outcome: fit(outcome, positive, BASE + [variable])
                      for outcome, positive in [('security', 'confident'), ('improved', 'improved'),
                                                 ('works', 'works well')]}
    return out
