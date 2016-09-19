echo(false);
alarm(#ulimitOmc#);

statFile := "#modelName#.stat";
writeFile("#logFile#","#modelName#\n",append=true);
writeFile(statFile + ".killed","Not exited cleanly");getErrorString();
writeFile(statFile + ".flat", "Killed");getErrorString();
writeFile(statFile + ".compile", "Killed");getErrorString();
writeFile(statFile + ".sim", "Killed");getErrorString();
writeFile(statFile + ".verify", "Killed");getErrorString();

outputFormat="default";
mslRegressionOutput:="";
loadModel(#modelName#, #modelVersion#);
reference_reltol:="+#reference_reltol#+";
reference_reltolDiffMinMax:="#reference_reltolDiffMinMax#";
reference_rangeDelta:="#reference_rangeDelta#";
simFlags:="#simFlags#";

referenceOK := false;
referenceFiles := "#referenceFiles#";
referenceCell := if referenceFiles == \"\" then \"\" else \"<td>&nbsp;</td>\";
reference := "#referenceFiles#/"+OpenModelica.Scripting.stringReplace("#modelName#",".",referenceFileNameDelimiter)+"."#referenceFileExtension#";
referenceExists := referenceFiles <> "" and regularFileExists(reference);
if not referenceExists then
  outputFormat := "empty";
end if;

compareVarsUri := "modelica://" + /*libraryString*/ "Buildings" + "/Resources/Scripts/OpenModelica/compareVars/#modelName#.mos";
(compareVarsFile,compareVarsFileMessages) := uriToFilename(compareVarsUri);

if regularFileExists(compareVarsFile) then
  runScript(compareVarsFile);
  vars := compareVars;
  variableFilter := sum(stringReplace(stringReplace(s,"[","."),"]",".") + "|" for s in vars) + "time";
  numCompared := size(vars,1);
  emit_protected := " -emit_protected";
elseif referenceExists then
  vars := readSimulationResultVars(reference, readParameters=true, openmodelicaStyle=true);
  variableFilter := sum(stringReplace(stringReplace(stringReplace(stringReplace(s,"[","."),"]","."),"(","."),")",".") + "|" for s in vars);
  numCompared := size(vars,1);
  emit_protected := " -emit_protected";
else
  variableFilter := "";
  outputFormat := "empty";
  emit_protected := "";
end if;

// Use twice as many output points as the experiment annotation suggests. Else aim for 5000 points.
(startTime,stopTime,tolerance,numberOfIntervals,stepSize):=getSimulationOptions(#modelName#,defaultTolerance="+String(default_tolerance)+",defaultNumberOfIntervals=2500);
numberOfIntervals := 2*numberOfIntervals;
alarm("+ulimitOmc+"); // Reset the alarm in case the other parts took a long time (reading simulation results)
res:=buildModel("+s+",tolerance=tolerance,outputFormat=outputFormat,numberOfIntervals=numberOfIntervals,variableFilter=variableFilter);
// We built the model fine, so reset the alarm. The simulation executable will also have an alarm, making only result verification a potential to stall.
alarm(0);

errFile:="files/#modelName#.err";
simFile:="files/#modelName#.sim";
(nmessage,nerror,nwarning) := countMessages();
errorLinkClass := if nerror>0 then "messagesError" elseif nwarning>0 then "messagesWarning" else "messagesInfo";
err:=getErrorString();
system("rm -f " + errFile);
writeFile(simFile,"");
if err <> "" then
  writeFile(errFile,err);
end if;

build    := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_BUILD_MODEL);
total    := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_SIMULATE_TOTAL);
templates:= OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_TEMPLATES);
simcode  := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_SIMCODE);
backend  := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_BACKEND);
frontend := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_FRONTEND);

frontend :=if backend <> -1.0 then frontend-backend else frontend;
backend  :=if simcode <> -1.0 then backend-simcode else backend;
simcode  :=if templates <> -1.0 then simcode-templates else simcode;
templates:=if build <> -1.0 then templates-build else templates;
timeDiff := -1.0;

OpenModelica.Scripting.Internal.Time.timerTick(OpenModelica.Scripting.Internal.Time.RT_CLOCK_USER_RESERVED);
buildRes := res[1] <> "";
simRes  := if not buildRes then false else 0 == system("./#modelName# "+simFlags+emit_protected+" > "+simFile+" 2>&1");

resFile := "#modelName#_res." + outputFormat;

system("sed -i '300,$ d' '" + simFile + "'"); // Only keep the top 300 lines
timeSim := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_USER_RESERVED);

if simRes then
  system("touch #modelName#.simsuccess");
  prefix := "files/#modelName#.diff";
  if referenceExists then
    OpenModelica.Scripting.Internal.Time.timerTick(OpenModelica.Scripting.Internal.Time.RT_CLOCK_USER_RESERVED);
    getErrorString();
    (referenceOK,diffVars) := diffSimulationResults(resFile,reference,prefix,relTol=reference_reltol,relTolDiffMinMax=reference_reltolDiffMinMax,rangeDelta=reference_rangeDelta);
    errVerify := getErrorString();
    if errVerify <> "" then
      writeFile(errFile, "\nVariables in the reference:"+sum(var+"," for var in OpenModelica.Scripting.readSimulationResultVars(reference, openmodelicaStyle=true)), append=true);
      writeFile(errFile, "\nVariables in the result:"+sum(var+"," for var in OpenModelica.Scripting.readSimulationResultVars(resFile))+"\n" + errVerify, append=true);
    end if;
    if referenceOK then
      system(\"touch "+s+".verifysuccess\");
    end if;
    timeDiff := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_USER_RESERVED);
    diffFiles := {prefix + \".\" + var for var in diffVars};
    // Create a file containing only the calibrated variables, for easy display
    if not referenceOK then
      timeDiff := OpenModelica.Scripting.Internal.Time.timerTock(OpenModelica.Scripting.Internal.Time.RT_CLOCK_USER_RESERVED);
      referenceCell := "<td bgcolor=\"#FF0000\">"+OpenModelica.Scripting.Internal.Time.readableTime(timeDiff)+\", <a href=\"files/#modelName#.diff.html\">\"+String(size(diffFiles,1))+"/"+String(numCompared)+" signals failed</a></td>";
      writeFile("files/#modelName#.diff.html","<html><body><h1>"+s+" differences from the reference file</h1><p>startTime: \"+String(startTime)+\"</p><p>stopTime: \"+String(stopTime)+\"</p><p>Simulated using tolerance: \"+String(tolerance)+\"</p><ul>\" + sum(\"<li>\"+csvFileToVariable(file)+\" <a href=\\\"\"+OpenModelica.Scripting.basename(file)+\".html\\\">(javascript)</a> <a href=\\\"\"+OpenModelica.Scripting.basename(file)+".csv\">(csv)</a></li>" for file in diffFiles) + "</ul></body></html>");
      {writeFile(prefix + "." + var + ".html","<html>
<head>
<script type=\"text/javascript\" src=\"dygraph-combined.js\"></script>
    <style type=\"text/css\">
    #graphdiv {
      position: absolute;
      left: 10px;
      right: 10px;
      top: 40px;
      bottom: 10px;
    }
    </style>
</head>
<body>
<div id=\"graphdiv\"></div>
<p><input type=checkbox id=\"0\" checked onClick=\"change(this)\">
<label for=\"0\">reference</label>
<input type=checkbox id=\"1\" checked onClick=\"change(this)\">
<label for=\"1\">actual</label>
<input type=checkbox id=\"2\" checked onClick=\"change(this)\">
<label for=\"2\">high</label>
<input type=checkbox id=\"3\" checked onClick=\"change(this)\">
<label for=\"3\">low</label>
<input type=checkbox id=\"4\" checked onClick=\"change(this)\">
<label for=\"4\">error</label>
<input type=checkbox id=\"5\" onClick=\"change(this)\">
<label for=\"5\">actual (original)</label>
Parameters used for the comparison: Relative tolerance "+String(reference_reltol)+" (local), "+String(reference_reltolDiffMinMax)+" (relative to max-min). Range delta "+String(reference_rangeDelta)+".</p>
<script type=\"text/javascript\">
g = new Dygraph(document.getElementById(\"graphdiv\"),
                 \""+OpenModelica.Scripting.basename(prefix + \".\" + var+".csv")+"\",{title: '"+var+"',
  legend: 'always',
  connectSeparatedPoints: true,
  xlabel: ['time'],
  y2label: ['error'],
  series : { 'error': { axis: 'y2' } },
  colors: ['blue','red','teal','lightblue','orange','black'],
  visibility: [true,true,true,true,true,false]
});
function change(el) {
  g.setVisibility(parseInt(el.id), el.checked);
}
</script>
</body>
</html>") for var in diffVars};

    else
      referenceCell := "<td bgcolor=\"#00FF00\">"+OpenModelica.Scripting.Internal.Time.readableTime(timeDiff)+" ("+String(numCompared)+" signals)</td>";
    end if;
  end if;
end if;