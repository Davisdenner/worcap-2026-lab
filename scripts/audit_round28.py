"""Auditoria independente das perdas, rankings e políticas da rodada 28."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score

from src.competition import CACHE, ROOT, save_json
from src.round2 import target_origins
from src.round25 import component_maps

YEARS=(2009,2011,2013,2015,2017,2019)
EVAL=YEARS[1:]
GRID=301*261
NORTH=np.arange(240*261,GRID)
OUT=ROOT/'reports/competition/round28'
ART=ROOT/'data/processed/round28'
REF=ROOT/'data/processed/round20'
ANALOG=ROOT/'data/processed/round25'
PREV=ROOT/'data/processed/round27'
COMP_NAMES=('s02','modes','local18','pls16','tropical_extension')
REG_NAMES=('ridge_G','ridge_clip','ridge_signedlog','ridge_logpositive','hgb_G','hgb_clip')
STRONG_NAMES=('logistic_base','hgb_full')


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def equal(x:float,y:float,atol:float=1e-7)->None:
    if not np.isclose(x,y,rtol=1e-7,atol=atol):
        raise AssertionError(f'{x} != {y}')


def main()->None:
    protocol=json.loads((OUT/'protocol.json').read_text(encoding='utf-8'))
    assert protocol['protocol_sha256']==sha(ROOT/'experiments/ROUND28.md')
    tp=np.load(CACHE/'tp.npy',mmap_mode='r').reshape(-1,GRID)
    decomp=json.loads((OUT/'decomposition.json').read_text(encoding='utf-8'))
    experts=json.loads((OUT/'experts.json').read_text(encoding='utf-8'))
    policy=json.loads((OUT/'policy.json').read_text(encoding='utf-8'))
    decision=json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
    all_g=[]
    all_l12=[]
    previous_positive=[]
    policy_sse={key:0. for key in policy['topk']}
    policy_counts={key:{'blocks':0,'years':0,'months':0} for key in policy['topk']}
    baseline_sse=0.
    checked_regression=0
    checked_strong=0
    checked_policies=0
    max_G_rounding=0.
    expert_sse={name:{'pure':0.,'pair':0.,'triple':0.} for name in COMP_NAMES}
    for year in YEARS:
        source_paths={name:ROOT/f'data/processed/round9/{year}_{name}.npy'
                      for name in COMP_NAMES[:4]}
        source_paths['s09']=ROOT/f'data/processed/round10/{year}_s09.npy'
        source_paths['fine32']=ROOT/f'data/processed/round11/{year}_fine32.npy'
        for name,path in source_paths.items():
            assert experts['source_hashes'][str(year)][name]==sha(path)
        files={'s12':REF/f'{year}_s12.npy','analog':ANALOG/f'{year}_h4_prediction.npy'}
        if year in EVAL:files['round27_winner']=PREV/f'{year}_winner_oof.npz'
        for name,path in files.items():
            assert protocol['input_hashes'][str(year)][name]==sha(path)
        origins=target_origins(year)+1
        assert origins.max()<972
        target=np.asarray(tp[origins],np.float64)
        s12=np.asarray(np.load(files['s12'],mmap_mode='r').reshape(24,GRID),np.float64)
        analog=np.asarray(np.load(files['analog'],mmap_mode='r').reshape(24,GRID),np.float64)
        l12=(target-s12)**2
        la=(target-analog)**2
        g=l12-la
        all_g.append(g.astype(np.float32))
        all_l12.append(l12.astype(np.float32))
        block=decomp['by_block'][str(year)]['global']
        equal(np.maximum(g,0).sum(),block['oracle_benefit_sse'],atol=.1)
        equal(l12.sum(),block['s12_sse'],atol=.1)
        previous_positive.append(g[:,NORTH][g[:,NORTH]>0].astype(np.float32))
        pieces=component_maps(year).astype(np.float64)
        for j,name in enumerate(COMP_NAMES):
            lc=(target-pieces[j])**2
            expert_sse[name]['pure']+=float(lc.sum())
            expert_sse[name]['pair']+=float(np.minimum(l12,lc).sum())
            expert_sse[name]['triple']+=float(np.minimum(np.minimum(l12,la),lc).sum())
        if year not in EVAL:continue
        report=json.loads((OUT/f'{year}_advantage.json').read_text(encoding='utf-8'))
        prior=np.concatenate(previous_positive[:-1])
        threshold=float(np.quantile(prior,.9))
        equal(threshold,report['strong_win_threshold_prior_north'],atol=1e-5)
        archive=ART/f'{year}_advantage_oof.npz'
        metadata=json.loads(archive.with_suffix('.json').read_text(encoding='utf-8'))
        assert sha(archive)==metadata['sha256']
        assert metadata['last_training_target']==f'{year-1}-12'
        with np.load(archive) as saved:
            saved_g=np.asarray(saved['G'],np.float64)
            scores=np.asarray(saved['regression'],np.float64)
            strong=np.asarray(saved['strong_probability'],np.float64)
            strong_label=np.asarray(saved['strong_label'],bool)
        truth_g=g[:,NORTH]
        max_G_rounding=max(max_G_rounding,float(np.max(np.abs(saved_g-truth_g))))
        np.testing.assert_allclose(saved_g,truth_g,rtol=2e-6,atol=.001)
        np.testing.assert_array_equal(strong_label,truth_g>threshold)
        for j,name in enumerate(REG_NAMES):
            row=report['scores'][name]
            p=scores[j].ravel()
            actual=truth_g.ravel()
            prior_mean=report['transformation']['mean_G_training']
            r2=1-np.sum((actual-p)**2)/np.sum((actual-prior_mean)**2)
            equal(r2,row['block']['r2_against_training_mean'],atol=1e-4)
            ordered=np.argsort(p,kind='stable')[::-1]
            selected=ordered[:int(np.ceil(.1*len(ordered)))]
            equal(float(actual[selected].mean()),
                  row['top_predicted'][3]['mean_G'],atol=1e-3)
            checked_regression+=1
        for j,name in enumerate(STRONG_NAMES):
            p=np.clip(strong[j].ravel(),.01,.99)
            y=strong_label.ravel()
            row=report['strong_win_metrics'][name]['block']
            equal(roc_auc_score(y,p),row['auc'])
            equal(average_precision_score(y,p),row['average_precision'])
            equal(np.mean((y-p)**2),row['brier'])
            ordered=np.argsort(p,kind='stable')
            top=ordered[-len(y)//10:]
            equal(y[top].mean()/y.mean(),row['top_decile_lift'])
            checked_strong+=1
        baseline_sse+=float(l12.sum())
        delta=analog[:,NORTH]-s12[:,NORTH]
        rn=target[:,NORTH]-s12[:,NORTH]
        baseline_north=float(np.sum(rn*rn))
        for key,row in policy['topk'].items():
            model='hgb_full' if key.startswith('strong_hgb_full') else 'logistic_base'
            k=float(key.split('_k')[1].split('_a')[0])/100
            alpha=float(key.split('_a')[1])
            score=strong[STRONG_NAMES.index(model)].ravel()
            ordered=np.argsort(score,kind='stable')[::-1]
            selected=np.zeros(len(score),bool)
            selected[ordered[:int(np.ceil(k*len(score)))]]=True
            changed=alpha*selected.reshape(24,len(NORTH))*delta
            total=float(l12.sum()-baseline_north+
                        np.sum((rn-changed)**2))
            policy_sse[key]+=total
            by_month=np.sum(l12,axis=1)-np.sum(rn*rn,axis=1)+\
                     np.sum((rn-changed)**2,axis=1)
            base_month=np.sum(l12,axis=1)
            policy_counts[key]['blocks']+=int(total<l12.sum())
            policy_counts[key]['months']+=int(np.sum(by_month<base_month))
            policy_counts[key]['years']+=sum(
                int(by_month[12*i:12*(i+1)].sum()<
                    base_month[12*i:12*(i+1)].sum()) for i in (0,1))
            equal(np.sqrt(total/(24*GRID)),
                  np.sqrt((1-row['by_block_gain_percent'][str(year)]/100)**2*
                          l12.sum()/(24*GRID)),atol=1e-7)
            checked_policies+=1
        print('AUDIT',year,flush=True)
    full_g=np.concatenate([x.ravel() for x in all_g]).astype(np.float64)
    full_l12=np.concatenate([x.ravel() for x in all_l12]).astype(np.float64)
    equal(np.maximum(full_g,0).sum(),decomp['global']['oracle_benefit_sse'],atol=.1)
    equal(full_l12.sum(),decomp['global']['s12_sse'],atol=.1)
    order=np.argsort(np.abs(full_g))[::-1]
    for fraction in (.01,.025,.05,.1,.2,.5):
        label=f'{100*fraction:g}%'
        selected=order[:int(np.ceil(fraction*len(order)))]
        benefit=np.maximum(full_g[selected],0).sum()/np.maximum(full_g,0).sum()
        equal(benefit,decomp['global']['top_abs_G'][label]
              ['oracle_benefit_fraction'],atol=1e-6)
    for name,row in experts['components'].items():
        for key in ('pure','pair','triple'):
            equal(expert_sse[name][key],row['global'][key],atol=.1)
    n=5*24*GRID
    equal(np.sqrt(baseline_sse/n),policy['baselines']['s12'])
    for key,row in policy['topk'].items():
        equal(np.sqrt(policy_sse[key]/n),row['global_rmse'])
        assert policy_counts[key]['blocks']==row['positive_blocks']
        assert policy_counts[key]['years']==row['positive_years']
        assert policy_counts[key]['months']==row['positive_months']
    signatures=json.loads((OUT/'signatures.json').read_text(encoding='utf-8'))
    for year in EVAL:
        for feature in ('climatology','member_std','analog_minus_s12','continental_pc_1'):
            count=sum(row['count'] for row in signatures['rows']
                      if row['cutoff']==year and row['feature']==feature)
            assert count==24*len(NORTH)
    assert decision['classification']=='D'
    assert not policy['continuous_rank_signal']
    assert len(policy['strong_win_signal'])==2
    assert not policy['expected_gain_tested']
    save_json(OUT/'audit.json',{
        'protocol_and_input_hashes_verified':True,
        'global_and_block_oracle_decomposition_recomputed':True,
        'all_prior_strong_thresholds_recomputed':True,
        'regression_and_strong_win_scores_recomputed':True,
        'all_topk_policies_recomputed':True,
        'component_oracles_recomputed':True,
        'all_targets_by_2020_12':True,
        'regression_checks':checked_regression,'strong_checks':checked_strong,
        'policy_block_checks':checked_policies,
        'max_saved_G_float32_rounding':max_G_rounding,
        'classification':decision['classification'],
        'source_sha256':sha(ROOT/'src/round28.py'),
        'audit_script_sha256':sha(ROOT/'scripts/audit_round28.py'),
    })
    print('ROUND28 AUDIT OK',flush=True)


if __name__=='__main__':main()
