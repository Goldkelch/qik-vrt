# Optional portable Python location

V45.12 does not require Python for normal Windows local verification or real GitHub
automation. The primary path is PowerShell-only.

If you still want Python helpers, place a portable Python runtime here:

```text
.\\python\\python.exe
```

Then run the preserved historical launcher:

```cmd
legacy\\v45\\QIKVRT_V45_12_RUN_PYTHON_VERIFY_OPTIONAL.cmd
```

The optional resolver must never expose Windows alias exit code 9009 as repository
verification failure.
