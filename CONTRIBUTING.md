# Contributing to geopalette

Contributions are welcome! Here's how to get started.

## Development setup

```bash
git clone https://github.com/igorpawelec/geopalette.git
cd geopalette
conda env create -f environment.yaml
conda activate geopalette
pip install -e .
```

## Running tests

```bash
pytest tests/
```

## Adding a new color space

1. Add the conversion function to `geopalette/conversions.py`
2. Register it in the `_CONVERSIONS` dictionary
3. Add it to the `__init__.py` imports
4. Add a test in `tests/test_conversions.py`
5. Update `README.md` with the new space

## Code style

- Follow PEP 8
- Use NumPy-style docstrings
- All functions operate on 2-D NumPy arrays

## Pull requests

- Fork the repo and create a feature branch
- Include tests for new functionality
- Update the CHANGELOG.md

## Releasing

The checklist exists because of a specific failure. `max_iters` changed
default in 0.3.0, and that one change broke CI in two packages at once —
pyHRG with `int | None`, which is a runtime `TypeError` before Python 3.10
while the metadata claims `>=3.9`, and rHRG with a stale `man/` page. Neither
was noticed. **pyHRG then tagged 0.3.0, 0.4.0 and 0.5.0 with the workflow
red**, so three releases could not be imported on the minimum Python they
advertise. rHRG shipped two the same way, rgeoadaptels two more.

Local tests passed in every one of those cases. They were run on one
interpreter, on one operating system, by someone who already knew what the
change was meant to do. The matrix is the part that disagrees.

1. Update `CHANGELOG.md`. If the output changes, say so in those words.
2. Bump the version everywhere it appears. Search for the *old* number and
   read the hits — `grep -rn "0.4.0" --exclude-dir=.git` — rather than
   editing the two or three places you remember.
3. Run the tests locally.
   Mind the oldest Python in `requires-python`: `X | Y` in an annotation
   is a runtime expression before 3.10 and will not import there, however
   cleanly it runs on your interpreter.
4. Commit and push. **Do not tag yet.**
5. **Wait for Actions on the pushed commit and confirm every matrix job is
   green.** Not the previous run, not the branch generally — that commit.
   This is the step that was missing. Either open the Actions tab, or:

   ```bash
   curl -s "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=1" |
     python -c "import json,sys; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['head_sha'][:7], r['status'], r['conclusion'])"
   ```

   `gh run list` is nicer if the GitHub CLI is installed; it is not
   everywhere, and the curl form needs nothing but a public repo.
6. Only then tag and push the tag:
   `git tag -a vX.Y.Z -m "..." && git push --tags`

The order matters. A tag is what people install and what a DOI points at, so
it should never be the thing that discovers a broken build. If Actions is
red, fix it and release the fix as its own version — the broken tag stays in
history either way.
