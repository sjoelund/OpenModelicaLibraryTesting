function toJSON
  input Real parsing, frontend, backend, simcode, templates, build, sim=-1.0, diff=-1.0;
  input String diffVars[:] = fill("", 0);
  output String json;
algorithm
  json := "{
  \"parsing\":"+String(parsing)+",
  \"frontend\":"+(if frontend <> -1.0 then String(frontend) else "null")+",
  \"backend\":"+(if backend <> -1.0 then String(backend) else "null")+",
  \"simcode\":"+(if simcode <> -1.0 then String(simcode) else "null")+",
  \"templates\":"+(if templates <> -1.0 then String(templates) else "null")+",
  \"build\":"+(if build <> -1.0 then String(build) else "null")+",
  \"sim\":"+(if sim <> -1.0 then String(sim) else "null")+",
  \"diff\":"+(if diff <> -1.0 then ("{\"time\":"+String(diff)+",\"vars\":["+sum(v + "," for v in diffVars)+"]}") else "null")+"
}
";
end toJSON;
