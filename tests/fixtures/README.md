# Test Fixtures

This directory contains real Qbox output files for testing parsers.

Each fixture should be a subdirectory with:
- `aiida.out` - stdout from Qbox run
- `qbox.xml` - XML output file
- `summary.json` - Expected parsed results (optional)

## Fixture Naming

| Fixture | Description |
|---------|-------------|
| `scf_converged/` | Successful SCF run |
| `scf_not_converged/` | SCF hit max iterations |
| `relax_converged/` | Geometry optimization converged |
| `md_complete/` | MD run completed target steps |
| `server_run/` | Server mode output |
| `oom_killed/` | Job killed by OOM |
| `walltime_killed/` | Job killed by walltime |

## Adding New Fixtures

1. Run a real Qbox calculation
2. Copy stdout and XML output to a new subdirectory
3. Add expected parsed results in `expected.json`
4. Add test case in `test_parsers_real_output.py`