<html>
<head>
  <title>#fileName# test using OpenModelica</title>
</head>
<body>
<h1>#fileName# test using OpenModelica</h1>

<table>
<th>
<td>Total</td>
<td>Frontend</td>
<td>Backend</td>
<td>SimCode</td>
<td>Templates</td>
<td>Compilation</td>
<td>Simulation</td>
<td>Verification</td>
</th>
<tr>
<td>#Total#</td>
<td>#Frontend#</td>
<td>#Backend#</td>
<td>#SimCode#</td>
<td>#Templates#</td>
<td>#Compilation#</td>
<td>#Simulation#</td>
<td>#Verification#</td>
</tr>
</table>

<p>Total time taken: #totalTime#</p>
<p>OpenModelica Version: #omcVersion#</p>
<p>Test started: #timeStart#</p>
<p>Tested Library: #libraryVersionRevision#</p>
<p>BuildModel time limit: #ulimitOmc#s</p>
<p>Simulation time limit: #ulimitExe#s</p>
<p>Default tolerance: #default_tolerance#</p>
Flags: <pre>#customCommands#</pre>
<p>Links are provided if getErrorString() or the simulation generates output. The links are coded with <font style="#FF0000">red</font> if there were errors, <font style="#FFCC66">yellow</font> if there were warnings, and normal links if there are only notifications.</p>
</body>
</html>
