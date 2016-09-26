#!/usr/bin/env python2

import os
import re
from joblib import Parallel, delayed
from subprocess import call
import time
import simplejson as json
import argparse

def multiple_replacer(*key_values):
    replace_dict = dict(key_values)
    replacement_function = lambda match: replace_dict[match.group(0)]
    pattern = re.compile("|".join([re.escape(k) for k, v in key_values]), re.M)
    return lambda string: pattern.sub(replacement_function, string)

def multiple_replace(string, *key_values):
    return multiple_replacer(*key_values)(string)

parser = argparse.ArgumentParser(description='OpenModelica library testing tool')
#parser.add_argument('--library', dest='accumulate', action='store_const',
#                    n_args=1, type=str, required=True,
#                    help='sum the integers (default: find the max)')

args = parser.parse_args()
print args.accumulate(args.integers)

from OMPython import OMCSession
omc = OMCSession()

omhome=omc.sendExpression('getInstallationDirectoryPath()')
omc_exe=os.path.join(omhome,"bin","omc")
dygraphs=os.path.join(omhome,"share","doc","omc","testmodels","dygraph-combined.js")
print(omc_exe,dygraphs)

# Create mos-files

library="Modelica"
res=omc.sendExpression('loadModel(%s)' % library)

customCommands = """
setCommandLineOptions("-d=nogen,initialization,backenddaeinfo,discreteinfo,stateselection,execstat");
setMatchingAlgorithm("PFPlusExt");
setIndexReductionMethod("dynamicStateSelection");
"""

referenceFiles=os.path.realpath(omhome+"/../testsuite/ReferenceFiles/msl32")
# None
referenceFileExtension="mat"
referenceFileNameDelimiter="."
default_tolerance=1e-6
reference_reltol=3e-3
reference_reltolDiffMinMax=3e-3
reference_rangeDelta=1e-3

libraryVersionRevision=omc.sendExpression('getVersion(%s)' % library)
libraryLastChange=""
librarySourceFile=omc.sendExpression('getSourceFile(%s)' % library)
lastChange=(librarySourceFile[:-3]+".last_change") if not librarySourceFile.endswith("package.mo") else (os.path.dirname(librarySourceFile)+".last_change")
print(lastChange)
if os.path.exists(lastChange):
  libraryLastChange = " %s (revision %s)" % (libraryVersionRevision,"\n".join(open(lastChange).readlines()).strip());
print(library+libraryLastChange)

sortFiles=True
ulimitOmc=660 # 11 minutes to generate the C-code
ulimitExe=480 # 8 additional minutes to initialize and run the simulation
ulimitMemory="16000000" # ~16GB memory at most
extraSimFlags="" # no extra sim flags
simFlags="-abortSlowSimulation -alarm=%d %s" % (ulimitExe,extraSimFlags)

print(res)
res=omc.sendExpression('setCommandLineOptions("-g=MetaModelica")')
print(res)
res=omc.sendExpression('{c for c guard isExperiment(c) and not regexBool(typeNameString(x), "^Modelica_Synchronous\\.WorkInProgress") in getClassNames(%s.Blocks.Examples, recursive=true)}' % library)
"""
print("Number of classes to build: " + String(size(a,1)));
system("rm -f *.o");
system("rm -f *.c");
system("rm -f *.h");
system("rm -rf "+libraryString+"*");
system("rm -rf files/ "+log);
mkdir("files");
"""

template = open("BuildModel.mos.tpl").read()

for c in res:
  replacements = (
    (u"#logFile#", "/tmp/OpenModelicaLibraryTesting.log"),
    (u"#modelName#", c),
    (u"#modelVersion#", libraryVersionRevision),
    (u"#ulimitOmc#", str(ulimitOmc)),
    (u"#default_tolerance#", str(default_tolerance)),
    (u"#reference_reltol#", str(reference_reltol)),
    (u"#reference_reltolDiffMinMax#", str(reference_reltolDiffMinMax)),
    (u"#reference_rangeDelta#", str(reference_rangeDelta)),
    (u"#simFlags#", str(simFlags)),
    (u"#referenceFiles#", str(referenceFiles or "")),
    (u"#referenceFileNameDelimiter#", referenceFileNameDelimiter),
    (u"#referenceFileExtension#", referenceFileExtension),
  )
  open(c + ".mos", "w").write(multiple_replace(template, *replacements))

def runScript(c):
  j = "files/%s.stat.json" % c
  if os.path.exists(j):
    os.remove(j)
  start=time.time()
  call([omc_exe, "%s.mos" % c])
  execTime=time.time()-start
  if os.path.exists(j):
    data=json.load(open(j))
    data["exectime"] = execTime
    json.dump(data, open(j,"w"))
  else:
    data = {"exectime":execTime}
    json.dump(data, open(j,"w"))

try:
  old_stats = json.load(open(".db"))
except:
  old_stats = {}

def expectedExec(c):
  v = (old_stats.get(c) or {}).get("exectime") or 0.0
  return v

res=sorted(res, key=lambda c: expectedExec(c), reverse=True)

cmd_res=[0]
start=time.time()
cmd_res=Parallel(n_jobs=4, backend="threading")(delayed(runScript)(c) for c in res)
stop=time.time()
print("Execution time: %.2f" % (stop-start))

#if max(cmd_res) > 0:
#  raise Exception("A command failed with exit status")

stats=dict([(c,json.load(open("files/"+c+".stat.json"))) for c in res])
for k in sorted(stats.keys(), key=lambda c: stats[c]["exectime"], reverse=True):
  print("%s: frontend %.2f" % (k, stats[k]["exectime"]))

json.dump(stats, open(".db","w"))

# Upload omc directory to build slaves


# Run jobs on slaves in parallel
