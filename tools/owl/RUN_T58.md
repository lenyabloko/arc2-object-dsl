# T58: one ELK classification run (Windows, PowerShell, no downloads)

Work from the repo root. The outbox only carries .txt, so first make working copies in a temp folder (nothing in the
repo changes): `mkdir $env:TEMP\t58; Copy-Item tools\owl\T58.java.txt $env:TEMP\t58\T58.java; Copy-Item tools\owl\T58.jsh.txt $env:TEMP\t58\T58.jsh; Copy-Item results\o0\t58_tbox.ofn.txt $env:TEMP\t58\t58_tbox.ofn`.
Do steps 1–2 from anywhere, then `Set-Location $env:TEMP\t58` before step 3; all step-3 commands use the local file
names. Afterwards copy `t58_taxonomy.tsv` to `cloud_outbox\wsl_results\t58\t58_taxonomy.tsv.txt`.
Rules: never download anything (no Maven, web, or Protégé plugin manager). Never read, print, or copy credentials,
tokens, or environment secrets. Leave the Protégé install unchanged. Report only the printed counts.

1. Find Protégé and the jars (read-only search). Protégé 5.6.1 keeps the OWL API in `bundles\`
   (`owlapi-osgidistribution-*.jar` / `owlapi-distribution-*.jar` / `org.semanticweb.owl.owlapi*.jar`), reasoner
   plugins in `plugins\` (ELK: `org.semanticweb.elk*.jar` / `elk-*.jar`), and a JRE in `jre\`. Plugins added later
   may be in `%USERPROFILE%\.Protege\plugins`.
   ```
   $P = "$env:USERPROFILE\Protege-5.6.1"      # the folder Len has; if it has no bundles\ subfolder, look one level down only
   if (-not (Test-Path "$P\bundles")) { $P = (Get-ChildItem $P -Directory -EA SilentlyContinue | ? { Test-Path "$($_.FullName)\bundles" } | Select -First 1).FullName }
   $elk = Get-ChildItem "$P","$env:USERPROFILE\.Protege" -Recurse -Filter "*elk*.jar" -EA SilentlyContinue | Select -First 1
   $jars = @(Get-ChildItem "$P\bundles" -Filter *.jar) + @(Get-ChildItem "$P\plugins" -Filter "*owlapi*.jar" -EA SilentlyContinue) + @($elk)
   $cp = ($jars.FullName | Select -Unique) -join ';'
   ```
   If there is no `$P`, no jar name matching `owlapi`, or no `$elk`, stop and report "blocked: no Protégé / OWL API / ELK jar".
2. Find Java. Look for javac with `$javac = (Get-Command javac -EA SilentlyContinue).Source`, else use
   `"$env:JAVA_HOME\bin\javac.exe"` if it exists. If you found javac, set `$java` to the `java.exe` next to it.
   Otherwise set `$java = "$P\jre\bin\java.exe"` (this bundled JRE has no javac), or use `java` on PATH.
3. Run the first option that applies. Try each option once.
   a. javac found:
      `& $javac -cp $cp -d . T58.java` then
      `& $java -cp "$cp;." T58 t58_tbox.ofn t58_taxonomy.tsv`
   b. No javac, but `& $java -version` shows 11 or later. Use source-file mode, which uses the runtime's own
      compiler module and needs no javac binary:
      `& $java -cp $cp T58.java t58_tbox.ofn t58_taxonomy.tsv`
   c. Option b fails with "compiler not found" and `jshell.exe` sits next to `$java`:
      `& (Join-Path (Split-Path $java) jshell.exe) --class-path $cp T58.jsh`
   d. Otherwise report "blocked: no javac".
4. The run may fail with `NoClassDefFoundError` naming `org/semanticweb/elk/...` or `org/apache/log4j/...`.
   If so, the ELK bundle keeps its libraries inside the jar. Run `mkdir $env:TEMP\t58elk` and then
   `tar -xf $elk.FullName -C $env:TEMP\t58elk`. Append `;$env:TEMP\t58elk` plus every jar under that folder to `$cp`,
   and retry once. For any other exception, report "blocked: <first line of the exception>".
5. Report the lines from `=== T58 RESULT ===` to `=== END ===`. Compare them with `expected_classification` in
   `results\o0\t58_export_summary.json` (repo). The exporter predicts 525 named classes, 522 distinct, 3 equivalence sets,
   and 0 unsatisfiable. Pass means: the file loads, no exception is thrown, and the equivalence sets are printed.
