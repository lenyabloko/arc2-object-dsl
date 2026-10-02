# T58: one ELK classification run (Windows, PowerShell, no downloads) — revised Oct 2 (classpath fix)

Rules: never download anything (no Maven, web, or Protégé plugin manager). Never read, print, or copy credentials,
tokens, or environment secrets. Leave the Protégé install unchanged (read-only: listing and copying jars out of it to
a temp folder is fine). Report only the printed counts. Run once, after c44/c45 are finished.

0. Files: `mkdir $env:TEMP\t58b; tar -xzf C:\Users\lenya\arc_extended_arga\cloud_outbox\batch-0081\files.tar.gz -C $env:TEMP\t58b`
   then `Set-Location $env:TEMP\t58b`; copy `tools\owl\T58.java.txt` to `T58.java`, `tools\owl\T58.jsh.txt` to `T58.jsh`,
   `results\o0\t58_tbox.ofn.txt` to `t58_tbox.ofn` (all inside $env:TEMP\t58b).
1. Classpath = EVERY jar of the Protégé install, plus the jars embedded inside those jars. The previous run failed in
   OWLManager.createOWLOntologyManager with NoClassDefFoundError com/github/benmanes/caffeine/cache/Caffeine because
   only bundles\ and the ELK jar were on the path; OSGi bundles often carry their dependencies as nested jars.
   ```
   $P = "$env:USERPROFILE\Protege-5.6.1\Protege-5.6.1"
   $jars = @(Get-ChildItem $P -Recurse -Filter *.jar -EA SilentlyContinue) + @(Get-ChildItem "$env:USERPROFILE\.Protege" -Recurse -Filter *.jar -EA SilentlyContinue)
   mkdir $env:TEMP\t58lib -EA SilentlyContinue | Out-Null
   foreach ($j in $jars) { $inner = tar -tf $j.FullName 2>$null | Where-Object { $_ -like '*.jar' }
     if ($inner) { $d = Join-Path $env:TEMP\t58lib $j.BaseName; mkdir $d -EA SilentlyContinue | Out-Null; tar -xf $j.FullName -C $d $inner } }
   $all = @($jars.FullName) + @(Get-ChildItem $env:TEMP\t58lib -Recurse -Filter *.jar | % FullName)
   $cp = ($all | Select -Unique) -join ';'
   ```
   Check that Caffeine is now present: `$all | ? { (tar -tf $_ 2>$null) -match 'com/github/benmanes/caffeine/cache/Caffeine.class' } | Select -First 1`.
   If nothing prints, report "blocked: Caffeine not in the Protégé install" and stop.
2. Java: javac from PATH (found earlier: Java 11.0.19). `$java` = the java.exe next to it.
3. `& $javac -cp $cp -d . T58.java` then `& $java -cp "$cp;." T58 t58_tbox.ofn t58_taxonomy.tsv`
   (If javac fails with an error about a class it cannot find, report its first two lines and stop.)
4. If the run fails with another NoClassDefFoundError, search the classpath once for the missing class:
   `$all | ? { (tar -tf $_ 2>$null) -match '<missing/class/Path>.class' } | Select -First 1` — if found, it is already on
   $cp (report the line and stop); if not found, report "blocked: <class> not in the Protégé install".
5. Report the lines from `=== T58 RESULT ===` to `=== END ===` and copy `t58_taxonomy.tsv` to
   `C:\Users\lenya\arc_extended_arga\cloud_outbox\wsl_results\t58\t58_taxonomy.tsv.txt`.
   Expected (from the exporter, results\o0\t58_export_summary.json): 554 named classes, 551 distinct after
   classification, 3 equivalence sets, 0 unsatisfiable.
