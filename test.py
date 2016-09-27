#!/usr/bin/env python2

import sys
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
parser.add_argument('configs', nargs='*')

args = parser.parse_args()
configs = args.configs

if configs == []:
  print("Error: Expected at least one configuration file to start the library test")
  sys.exit(1)

def readConfig(c):
  data = json.load(open(c))
  data["referenceFileExtension"] = data.get("referenceFileExtension") or "mat"
  data["referenceFileNameDelimiter"] = data.get("referenceFileNameDelimiter") or "."
  data["default_tolerance"] = data.get("default_tolerance") or 1e-6
  data["reference_reltol"] = data.get("reference_reltol") or 3e-3
  data["reference_reltolDiffMinMax"] = data.get("reference_reltolDiffMinMax") or 3e-3
  data["reference_rangeDelta"] = data.get("reference_rangeDelta") or 1e-3
  data["customCommands"] = data.get("customCommands") or """
setCommandLineOptions("-d=nogen,initialization,backenddaeinfo,discreteinfo,stateselection,execstat");
setMatchingAlgorithm("PFPlusExt");
setIndexReductionMethod("dynamicStateSelection");
"""
  data["ulimitOmc"] = data.get("ulimitOmc") or 660 # 11 minutes to generate the C-code
  data["ulimitExe"] = data.get("ulimitExe") or 480 # 8 additional minutes to initialize and run the simulation
  data["ulimitMemory"] = data.get("ulimitMemory") or 16000000 # ~16GB memory at most
  data["extraSimFlags"] = data.get("extraSimFlags") or "" # no extra sim flags
  data["libraryVersion"] = data.get("libraryVersion") or "default"
  return (data["library"],data)

configs = [readConfig(c) for c in configs]

from OMPython import OMCSession
omc = OMCSession()

omhome=omc.sendExpression('getInstallationDirectoryPath()')
omc_exe=os.path.join(omhome,"bin","omc")
dygraphs=os.path.join(omhome,"share","doc","omc","testmodels","dygraph-combined.js")
print(omc_exe,dygraphs)

# Create mos-files

if not omc.sendExpression('setCommandLineOptions("-g=MetaModelica")'):
  print("Failed to set MetaModelica grammar")
  sys.exit(1)

tests=[]
for (library,conf) in configs:
  omc.sendExpression('clear()')
  if not omc.sendExpression('loadModel(%s,{"%s"})' % (library,conf["libraryVersion"])):
    print("Failed to load library: " + omc.sendExpression('getErrorString()'))
    sys.exit(1)
  conf["libraryVersionRevision"]=omc.sendExpression('getVersion(%s)' % library)
  conf["libraryLastChange"]="" # TODO: FIXME
  librarySourceFile=omc.sendExpression('getSourceFile(%s)' % library)
  lastChange=(librarySourceFile[:-3]+".last_change") if not librarySourceFile.endswith("package.mo") else (os.path.dirname(librarySourceFile)+".last_change")
  if os.path.exists(lastChange):
    conf["libraryLastChange"] = " %s (revision %s)" % (conf["libraryVersionRevision"],"\n".join(open(lastChange).readlines()).strip())
  res=omc.sendExpression('{c for c guard isExperiment(c) and not regexBool(typeNameString(x), "^Modelica_Synchronous\\.WorkInProgress") in getClassNames(%s.Blocks.Examples, recursive=true)}' % library)
  tests = tests + [(library,library+"_"+conf["libraryVersion"]+"_"+r,conf) for r in res]

"""
print("Number of classes to build: " + String(size(a,1)));
system("rm -f *.o");
system("rm -f *.c");
system("rm -f *.h");
system("rm -rf "+libraryString+"*");
system("rm -rf files/ "+log);
mkdir("files");
"""

print(tests)

template = open("BuildModel.mos.tpl").read()

for (library,name,conf) in tests:
  simFlags="-abortSlowSimulation -alarm=%d %s" % (conf["ulimitExe"],conf["extraSimFlags"])
  replacements = (
    (u"#logFile#", "/tmp/OpenModelicaLibraryTesting.log"),
    (u"#modelName#", library),
    (u"#modelVersion#", conf["libraryVersionRevision"]),
    (u"#ulimitOmc#", str(conf["ulimitOmc"])),
    (u"#default_tolerance#", str(conf["default_tolerance"])),
    (u"#reference_reltol#", str(conf["reference_reltol"])),
    (u"#reference_reltolDiffMinMax#", str(conf["reference_reltolDiffMinMax"])),
    (u"#reference_rangeDelta#", str(conf["reference_rangeDelta"])),
    (u"#simFlags#", simFlags),
    (u"#referenceFiles#", str(conf.get("referenceFiles") or "")),
    (u"#referenceFileNameDelimiter#", conf["referenceFileNameDelimiter"]),
    (u"#referenceFileExtension#", conf["referenceFileExtension"]),
  )
  open(name + ".mos", "w").write(multiple_replace(template, *replacements))

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
  (lib,name,data) = c
  v = (old_stats.get(name) or {}).get("exectime") or 0.0
  return v

tests=sorted(tests, key=lambda c: expectedExec(c), reverse=True)

cmd_res=[0]
start=time.time()
cmd_res=Parallel(n_jobs=4, backend="threading")(delayed(runScript)(name) for (lib,name,data) in tests)
stop=time.time()
print("Execution time: %.2f" % (stop-start))

#if max(cmd_res) > 0:
#  raise Exception("A command failed with exit status")

stats=dict([(name,json.load(open("files/%s.stat.json" % name))) for (lib,name,conf) in tests])
for k in sorted(stats.keys(), key=lambda c: stats[c]["exectime"], reverse=True):
  print("%s: frontend %.2f" % (k, stats[k]["exectime"]))

json.dump(stats, open(".db","w"))

# Upload omc directory to build slaves


# Run jobs on slaves in parallel
