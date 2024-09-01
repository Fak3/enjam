```
$ enjam --dst /tmp/crf{crf} --vcodec libaom-av1 --crf 24
Destination dir /tmp/crf24
Found 4 files
  ERR  /home/z/pproj/enjam/tests/empty-two.gif 100% 0:00:00
  0.2x /home/z/pproj/enjam/tests/64pix.gif     100% 0:00:00
  0.1x /home/z/pproj/enjam/tests/1pix.gif      100% 0:00:00
  ERR  /home/z/pproj/enjam/tests/empty-one.gif 100% 0:00:00
Average compression ratio: 0.1
All finished in 0:00:00.325396
Successfully processed 2 files
Failed to process 2 files
```

# Enjam

Batch convert video files.

```
Usage: enjam [OPTIONS]

  Batch convert videos.

Options:
  --src DIRECTORY                 [default: .]
  --dst TEXT                      Output directory path. Can include
                                  variables. Example: ./{vcodec}-{crf}
                                  [default: (src)]
  --exclude-dstdir                Do not pick source files from dstdir, if it
                                  is located inside srcdir   [default: True]
  --jobs INTEGER                  [default: 4]
  --acodec TEXT                   [default: copy]
  --vcodec [libaom-av1|librav1e|libsvtav1|libx264|libx265|copy]
                                  [default: libsvtav1]
  --vbitrate TEXT                 If stars with x, resulting bitrate is a
                                  ratio of input file resolution. Example:
                                  x2.3 or 200k
  --abitrate TEXT                 [default: 38k]
  --crf INTEGER                   Constant rate factor. Or qp for rav1e.
                                  [default: (24, if vbitrate is not set)]
  --speed TEXT                    [default: 7]
  --fprefix TEXT                  Output file prefix. Can include variables.
                                  If fprefix is not provided and dst dir
                                  includes variables, fprefix is set to the
                                  same pattern as dst dir name. Example:
                                  {vcodec}-{crf}-  [default: (f'{dst.name}-'
                                  if '{' in dst else None)]
  --gop INTEGER                   [default: 200]
  --grain INTEGER                 [default: 0]
  --write-log / --no-write-log    [default: write-log]
  --verbose / --no-verbose        [default: no-verbose]
  --skip-errors / --no-skip-errors
                                  Continue processing queue after one file
                                  error  [default: skip-errors]
  --pattern TEXT                  [default: *.gif]
  --install-completion            Install completion for the current shell.
  --show-completion               Show completion for the current shell, to
                                  copy it or customize the installation.
  --help                          Show this message and exit.
```

## Installation
```
pipx install enjam

enjam --install-completion
```


## Development
```
pdm venv create -n 11 3.11
eval $(pdm venv activate 11)

```

### Test
```
pytest -s --doctest-modules
```
