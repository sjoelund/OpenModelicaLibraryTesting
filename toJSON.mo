function toJSON
  input Real frontend, backend, simcode, templates, build, sim=-1.0, diff=-1.0;
  output String json;
algorithm
  json := "{
  \"frontend\":"+(if frontend <> -1.0 then String(frontend) else "null")+",
  \"backend\":"+(if backend <> -1.0 then String(backend) else "null")+",
  \"simcode\":"+(if simcode <> -1.0 then String(simcode) else "null")+",
  \"templates\":"+(if templates <> -1.0 then String(templates) else "null")+",
  \"build\":"+(if build <> -1.0 then String(build) else "null")+",
  \"sim\":"+(if sim <> -1.0 then String(sim) else "null")+",
  \"diff\":"+(if diff <> -1.0 then String(diff) else "null")+"
}
";
end toJSON;
