# Environment

Two interpreters, on purpose:

1. **SimNIBS bundled Python (`simnibs_python`)** — runs the simulation pipeline (`s01`–`s07`).
   `simnibs` only imports here. Install our helpers into it:
   ```bash
   simnibs_python -m pip install -r env/requirements.txt
   ```

2. **(Optional) A standalone analysis env** (`env/environment.yml`) — for stats/figures if you
   prefer to keep `s08`/notebooks out of the SimNIBS interpreter. Everything upstream of the
   `metrics.csv` still needs `simnibs_python`.

Full install walkthrough and the Ernie smoke test: [../docs/06_environment_setup.md](../docs/06_environment_setup.md).

After Week 1, **pin exact versions** here and in `requirements.txt`, and record them in
`docs/04_methods_protocol.md` for the preregistration.
