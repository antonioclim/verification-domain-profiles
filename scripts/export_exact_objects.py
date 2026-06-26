#!/usr/bin/env python3
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from mmor_certificates.oracles import ExplicitOracle
from mmor_certificates.profile import classify_minimum_budget, fixed_budget_row_generation, minimum_budget_row_generation
from run_computational_study import build_correctness_cases, profile_budgets, PROTOCOL_SHA256

CERT=ROOT/'results/certificates'; PROF=ROOT/'results/profiles'; INST=ROOT/'results/instances'
for directory in (CERT, PROF, INST): directory.mkdir(parents=True, exist_ok=True)
for p in list(CERT.glob('*.json'))+list(PROF.glob('*.json'))+list(INST.glob('*.json')): p.unlink()
count=profiles=0
for case_id,instance,oracle,expected,family in build_correctness_cases():
    (INST/f'{case_id}.json').write_text(json.dumps(instance.to_json(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    result=minimum_budget_row_generation(oracle)
    payload={
      'schema':'mmor-minimum-budget-certificate-1.0',
      'case_id':case_id,
      'family':instance.family,
      'instance_digest':instance.digest(),
      'classification':classify_minimum_budget(result),
      'result':result.to_json(),
      'protocol_sha256':PROTOCOL_SHA256
    }
    if payload['classification']!=expected:raise AssertionError(case_id)
    (CERT/f'{case_id}.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    count+=1
    for idx,budget in enumerate(profile_budgets(payload['classification'],result.budget)):
      profile=fixed_budget_row_generation(oracle,budget)
      pp={
       'schema':'mmor-profile-record-1.0','case_id':case_id,'family':instance.family,
       'instance_digest':instance.digest(),'protocol_sha256':PROTOCOL_SHA256,
       'result':profile.to_json()
      }
      (PROF/f'{case_id}-b{idx}.json').write_text(json.dumps(pp,indent=2,sort_keys=True)+'\n',encoding='utf-8')
      profiles+=1
print(json.dumps({'instances':count,'certificates':count,'profiles':profiles},indent=2))
