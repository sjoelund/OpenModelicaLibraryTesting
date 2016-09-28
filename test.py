#!/usr/bin/env python2

# TODO: When libraries hash changes, run with the old OMC against the new libs
#       Then run with the new OMC against the new libs

import sys
import os
import re
from joblib import Parallel, delayed
from subprocess import call
import time
import simplejson as json
import argparse
import sqlite3

def multiple_replacer(*key_values):
    replace_dict = dict(key_values)
    replacement_function = lambda match: replace_dict[match.group(0)]
    pattern = re.compile("|".join([re.escape(k) for k, v in key_values]), re.M)
    return lambda string: pattern.sub(replacement_function, string)

def multiple_replace(string, *key_values):
    return multiple_replacer(*key_values)(string)

parser = argparse.ArgumentParser(description='OpenModelica library testing tool')
parser.add_argument('configs', nargs='*')
parser.add_argument('--branch', default='master')

args = parser.parse_args()
configs = args.configs
branch = args.branch

if configs == []:
  print("Error: Expected at least one configuration file to start the library test")
  sys.exit(1)

def fixData(data):
  data["referenceFileExtension"] = data.get("referenceFileExtension") or "mat"
  data["referenceFileNameDelimiter"] = data.get("referenceFileNameDelimiter") or "."
  data["default_tolerance"] = data.get("default_tolerance") or 1e-6
  data["reference_reltol"] = data.get("reference_reltol") or 3e-3
  data["reference_reltolDiffMinMax"] = data.get("reference_reltolDiffMinMax") or 3e-3
  data["reference_rangeDelta"] = data.get("reference_rangeDelta") or 1e-3
  defaultCustomCommands = """
setCommandLineOptions("-d=nogen,initialization,backenddaeinfo,discreteinfo,stateselection,execstat");
setMatchingAlgorithm("PFPlusExt");
setIndexReductionMethod("dynamicStateSelection");
"""
  data["customCommands"] = (data.get("customCommands") or defaultCustomCommands) + (data.get("extraCustomCommands") or "")
  data["ulimitOmc"] = data.get("ulimitOmc") or 660 # 11 minutes to generate the C-code
  data["ulimitExe"] = data.get("ulimitExe") or 10 # 8 additional minutes to initialize and run the simulation
  data["ulimitMemory"] = data.get("ulimitMemory") or 16000000 # ~16GB memory at most
  data["extraSimFlags"] = data.get("extraSimFlags") or "" # no extra sim flags
  data["libraryVersion"] = data.get("libraryVersion") or "default"
  return (data["library"],data)

def readConfig(c):
  return [fixData(data) for data in json.load(open(c))]

configs_lst = [readConfig(c) for c in configs]
configs = []
for c in configs_lst:
  configs = configs + c

from OMPython import OMCSession
omc = OMCSession()

omhome=omc.sendExpression('getInstallationDirectoryPath()')
omc_exe=os.path.join(omhome,"bin","omc")
omc_version=omc.sendExpression('getVersion()')
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
  res=omc.sendExpression('{c for c guard isExperiment(c) and not regexBool(typeNameString(x), "^Modelica_Synchronous\\.WorkInProgress") in getClassNames(%s.Blocks.Examples.PID_Controller, recursive=true)}' % library)
  libName=library+"_"+conf["libraryVersion"]+(("_" + conf["configExtraName"]) if conf.has_key("configExtraName") else "")
  tests = tests + [(r,library,libName,libName+"_"+r,conf) for r in res]

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

for (modelName,library,libName,name,conf) in tests:
  simFlags="-abortSlowSimulation -alarm=%d %s" % (conf["ulimitExe"],conf["extraSimFlags"])
  replacements = (
    (u"#logFile#", "/tmp/OpenModelicaLibraryTesting.log"),
    (u"#library#", library),
    (u"#modelName#", modelName),
    (u"#fileName#", name),
    (u"#customCommands#", conf["customCommands"]),
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
  call([omc_exe, "-n=1", "%s.mos" % c])
  execTime=time.time()-start
  if os.path.exists(j):
    data=json.load(open(j))
    data["exectime"] = execTime
    json.dump(data, open(j,"w"))
  else:
    data = {"exectime":execTime}
    json.dump(data, open(j,"w"))

conn = sqlite3.connect('sqlite3.db')
cursor = conn.cursor()
# BOOLEAN NOT NULL CHECK (verify IN (0,1) AND builds IN (0,1) AND simulates IN (0,1))
cursor.execute('''CREATE TABLE if not exists %s
             (date integer, libname text, model text, exectime real, frontend real, backend real, simcode real, templates real, compile real, verify real, verifyfail integer, finalphase integer)''' % branch)
try:
  old_stats = json.load(open(".db"))
except:
  old_stats = {}

def expectedExec(c):
  (model,lib,libName,name,data) = c
  #v = (old_stats.get(name) or {}).get("exectime") or 0.0
  #return v
  cursor.execute("SELECT exectime,libname,model,date FROM %s WHERE libname = ? AND model = ? ORDER BY date DESC LIMIT 1" % branch, (libName,model))
  print "SELECT",(libName,model)
  v = cursor.fetchone()
  print v
  return v or 0.0

tests=sorted(tests, key=lambda c: expectedExec(c), reverse=True)

cmd_res=[0]
start=time.time()
testRunStartTimeAsEpoch = int(start)
cmd_res=Parallel(n_jobs=4)(delayed(runScript)(name) for (model,lib,libName,name,data) in tests)
stop=time.time()
print("Execution time: %.2f" % (stop-start))

#if max(cmd_res) > 0:
#  raise Exception("A command failed with exit status")

stats=dict([(name,(model,libname,json.load(open("files/%s.stat.json" % name)))) for (model,lib,libname,name,conf) in tests])
for k in sorted(stats.keys(), key=lambda c: stats[c][2]["exectime"], reverse=True):
  print("%s: exectime %.2f" % (k, stats[k][2]["exectime"]))

#new_stats = old_stats
for key in stats.keys():
  #new_stats[key] = stats[key][2]
  (model,libname,data)=stats[key]
  print(model,libname)
  cursor.execute("INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?)" % branch,
    (testRunStartTimeAsEpoch,
    libname,
    model,
    data["exectime"],
    data["frontend"],
    data["backend"],
    data["simcode"],
    data["templates"],
    data["build"],
    (data.get("diff") or {}).get("time") or 0.0,
    len((data.get("diff") or {}).get("vars") or []),
    -1
  ))
  conn.commit()
for row in cursor.execute('SELECT * FROM %s ORDER BY date' % branch):
  print row
conn.close()
#json.dump(new_stats, open(".db","w"))

# Upload omc directory to build slaves


# Run jobs on slaves in parallel
