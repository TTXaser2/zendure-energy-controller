#!/usr/bin/env python3
"""Run explicitly scoped V18 installable release tests without deleting historical fixtures.

Test exceptions are published in validation/V18_RELEASE_APPLICABILITY.json.
They were independently exercised on their corresponding CP42 stage or V17 source.
"""
import os,sys,json,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
for x in (root,root/'tools',root/'tests'):sys.path.insert(0,str(x))
class Counter(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.subtests=0
 def addSubTest(self,test,subtest,err):
  self.subtests+=1
  return super().addSubTest(test,subtest,err)
def flatten(s):
 for x in s:
  if isinstance(x,unittest.TestSuite):yield from flatten(x)
  else:yield x
rules=json.loads((root/'validation/V18_RELEASE_APPLICABILITY.json').read_text())
excluded={(x['source'],x['test']) for x in rules['excluded']}
suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py',top_level_dir=str(root))
selected=[];skipped=[]
for t in flatten(suite):
 module=t.__class__.__module__
 name=t._testMethodName
 if (module+'.'+t.__class__.__name__+'.'+name,name) in excluded or (module.removeprefix('tests.')+'.'+t.__class__.__name__+'.'+name,name) in excluded:
  skipped.append((module,name))
 else:selected.append(t)
if len(skipped)!=rules['excluded_count'] or len(excluded)!=len(skipped):
 print('EXCLUSION_CONTRACT_MISMATCH',len(skipped),len(excluded));sys.exit(3)
results=unittest.TextTestRunner(verbosity=1,resultclass=Counter).run(unittest.TestSuite(selected))
report={'complete':True,'status':'PASS' if results.wasSuccessful() else 'FAIL','tests':results.testsRun,'subtests':results.subtests,'errors':len(results.errors),'failures':len(results.failures),'excluded_historical_assertions':len(skipped),'warnings_mode':'error::ResourceWarning' if 'error::ResourceWarning' in sys.warnoptions else 'default'}
out=os.environ.get('ZEC_QA_OUTPUT')
if out:Path(out).write_text(json.dumps(report,indent=2)+'\n')
print('ZEC_V18_FIELD_QA='+json.dumps(report))
sys.exit(0 if results.wasSuccessful() else 1)
