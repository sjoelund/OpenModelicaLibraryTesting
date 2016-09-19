#!/usr/bin/env python2

import os
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

referenceFiles=None
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
res=omc.sendExpression('{c for c guard isExperiment(c) and not regexBool(typeNameString(x), "^Modelica_Synchronous\\.WorkInProgress") in getClassNames(Modelica, recursive=true)}')
"""
print("Number of classes to build: " + String(size(a,1)));
system("rm -f *.o");
system("rm -f *.c");
system("rm -f *.h");
system("rm -rf "+libraryString+"*");
system("rm -rf files/ "+log);
mkdir("files");
"""
for c in res:
  pass # print(c)

# Upload omc directory to build slaves


# Run jobs on slaves in parallel
