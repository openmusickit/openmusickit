## Outcome (2026-11-05)

Released. `pip install openmusickit` gives 0.1.0, and the docs are deployed to openmusickit.org.

- **PyPI:** <https://pypi.org/project/openmusickit/0.1.0/>,
  published by [this run](https://github.com/openmusickit/openmusickit/actions/runs/42039642092)
  from `47986d9` on `release/0.1.0`, tagged `v0.1.0`, with a GitHub release.
- **Heavy set:** 4,319 passed on the baseline here (`42d460f`, Python 3.12, 17:11).
  On GitHub, 4,310 passed and 9 skipped on each of 3.12, 3.13, 3.14 and 3.15 (19 to 23 minutes each);
  the skips are the MuseScore tests.
- **Checked from outside:** `pip install` in a new environment gave 0.1.0,
  all 86 modules imported, and the README's MusicXML example ran on a real score.
- **Docs:** first deploy succeeded (the docs build takes about 10 minutes on GitHub).

Differences from the plan:

- The docs build takes about 10 minutes on GitHub, not the 2 it takes here.
- `adamwood@google.com` is only the author field on the 2022 releases, not the account's email.
  The warning about it in this plan was a mistake and has been removed.


## Requirements
from the developer


- Quarto docs site deployed via GH Pages, on domain openmusickit.org

- PyPi package at openmusickit, version number 0.1.0

- GH action for release to PyPI, based on a versioned release branch and some (for now) manual "push the button to go"
  - full test suite runs on all supported major Python versions (i *think* we decided >=3.12) before release is sent to PyPi

- GH action for docs update
  - run the short test suite and the verify via build process that the in-docs code works
  - docs are built and deployed whenever changes to the /docs/ directory are pushed to main

- repo edits for you to make:
  - update install instructions and any links; fix anything that is made out of date by the release itself
  - update pyproject with version number
  - copy the (updated) contents of index.qmd and basics.md to the README, with links to PyPi and OpenMusicKit.org


## Additional requirements
from Claude, each from something found while checking the repo on 2026-11-05

**Packaging**

- Fill in `[project.urls]`, which is currently commented out,
  so the PyPI page links to the docs and the repo.
- Add classifiers: Alpha status, Python 3.12 to 3.15, audience, topic.
- State the license as an SPDX expression
  (needs `setuptools>=77` in `build-system`).
- Replace the summary line, which PyPI will show for 0.1.0 permanently.
- Ship a `py.typed` marker.
  Without it, type checkers ignore OMK's annotations in downstream projects.
- Split `dev` into `test` and `docs` dependency groups, with `dev` including both.
  `quartodoc` needs `pydantic-core`, which will not build on Python 3.15,
  and only the docs job needs it.
- Add a `.python-version` of 3.14.
  Without one, `git clone` and `uv sync` fail for any contributor whose default Python is 3.15,
  for the same `pydantic-core` reason.
  This affects development only, not who can install OMK.

**Docs site**

- Fix the `goals.md` links in `docs/_quarto.yml` and `docs/index.qmd`;
  the file is `goals.qmd`.
  This one bad link produces 400 warnings in the build, and does not fail it.
- Fail the docs build on an unresolved link, so this cannot recur unnoticed.
- Keep `docs/Untitled.ipynb` off the site.
  It is currently rendered and would be published at `/Untitled.html`.

**Release**

- Publish with PyPI Trusted Publishing, so no API token exists to store or leak.
- Only `release/*` branches may publish, enforced by a `pypi` GitHub environment.
- Check the built wheel before publishing, by importing every module from it in a clean environment.
  The test jobs run against the source tree, so they would not notice a packaging fault.
- Tag `v0.1.0` and create a GitHub release after publishing,
  because PyPI versions are permanent and the tag records what went out.
- Pin actions to commit SHAs in both workflows.
  The release workflow can publish under the project's name.

**Corrections**

- `CHANGELOG.md` dates 0.0.1 as 2024-03-20; PyPI shows it was uploaded on 2022-01-31.
  Correct the date.
- Fix the small typos in `basics.md` while copying it
  ("how they related", "many musical system", "also mechanism").


## What was checked

All from fresh clones of `42d460f`, on 2026-11-05:

- Fast test set: 4,263 passed on each of Python 3.12, 3.13, 3.14 and 3.15.
  3.15 ran with the dependency split above applied in the scratch clone,
  using locked versions.
- Built wheel: all 86 modules import on all four Pythons, with only its declared dependencies.
- Docs: `build_reference.py` and `quarto render` both exit 0 on 3.12.
  The JSON schemas are copied into the site,
  so their `https://openmusickit.org/spec/schema/...` ids will resolve once the domain is live.
- Version: `pyproject.toml` and `uv.lock` already say 0.1.0, and 0.1.0 is unused on PyPI.

Not yet known:

- The heavy set on this commit (the baseline). It is running now.
- Whether the heavy set passes on GitHub's runners, which are slower than this machine.
- Whether the PyPI publisher is set up correctly.
  This can only be proved by the first publish.


## Decisions

Answered by the developer on 2026-11-05.

1. **License identifier:** `AGPL-3.0-only`.
2. **Docs deploy trigger:** pushes to `main` touching `docs/**` or `src/**`,
   because the API reference and executable pages are built from `src/`.
3. **`docs/Untitled.ipynb`:** excluded from the site; the file stays in the repo.
4. **Python versions:** test and claim 3.12 to 3.15.
5. **PyPI summary:** "A symbolic music representation library:
   scores as graphs of musical objects, at any level of completeness, in any musical system."
6. **Publishing 0.1.0:** Claude starts this one release run,
   which publishes only if every check passes.
   Later releases are the developer's to start.

Also approved: pushing directly to `main`.


## The plan

### Part 1: Claude, immediately after approval (about 2 minutes)

These come before your steps so that the domain is claimed on GitHub before DNS points at it.

1. Enable GitHub Pages with Actions as its source, and set the custom domain to `openmusickit.org`.
2. Create the `pypi` environment, restricted to `release/*` branches.

### Part 2: Developer (about 15 minutes, then you can leave)

**A. PyPI: add the trusted publisher.**
Sign in to the account that owns `openmusickit`.

At <https://pypi.org/manage/project/openmusickit/settings/publishing/>, add a GitHub publisher:

| Field | Value |
|---|---|
| Owner | `openmusickit` |
| Repository name | `openmusickit` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

The workflow does not exist yet, and PyPI does not require it to.

**B. NameSilo: point the domain at GitHub Pages.**
The domain has no MX, TXT or CAA records, so nothing else needs preserving.

Delete the parking records:

- the three `A` records on `openmusickit.org`
  (`198.251.81.30`, `209.141.38.71`, `107.161.23.204`)
- the `CNAME` on `www` (to `parking.namesilo.com`)

Add these, leaving the host blank except for `www`:

| Type | Host | Value |
|---|---|---|
| A | | `185.199.108.153` |
| A | | `185.199.109.153` |
| A | | `185.199.110.153` |
| A | | `185.199.111.153` |
| AAAA | | `2606:50c0:8000::153` |
| AAAA | | `2606:50c0:8001::153` |
| AAAA | | `2606:50c0:8002::153` |
| AAAA | | `2606:50c0:8003::153` |
| CNAME | `www` | `openmusickit.github.io` |

**C. GitHub: verify the domain (recommended).**
This stops anyone else's Pages site from claiming the domain.
At <https://github.com/organizations/openmusickit/settings/pages>, choose "Add a domain",
enter `openmusickit.org`, and add the TXT record it shows you at NameSilo.
The "Verify" button may not succeed until the record propagates,
so clicking it can wait until you are back.

**D. Leave this machine able to work.**
Keep it awake, with this Claude Code session open and you logged in.
Pushing and `gh` run from here,
so suspending the machine stops the work until you return.
A permission prompt would also pause it.

### Part 3: Claude, while you are away

3. Confirm the heavy baseline result.
   A failure already present is recorded in `_plans/revisit.md`
   and reported, and it stops the publish (see "If something goes wrong").
4. Make the repo edits, as separate commits with the `Claude:` prefix:
   - dependency groups, `uv.lock`, packaging metadata, `py.typed`
   - docs: `goals` links, notebook exclusion, install instructions in `index.qmd`
     (`pip install openmusickit`, keeping the from-source route for contributors),
     typos, and a deployment note in `docs/README.md`
   - `README.md`: `index.qmd` and `basics.md`, plus links to PyPI and openmusickit.org.
     Relative links become absolute, because they would break on PyPI.
     The MusicXML example stays, with its link updated.
   - `CHANGELOG.md`: your edit, plus the date correction
   - `.github/workflows/docs.yml` and `release.yml`, with the release steps
     written as a comment at the top of `release.yml`
5. Check locally: fast test set, `uv build`, wheel contents including `py.typed`,
   a clean docs render, and the README code examples.
6. Push to `main` directly, as this repo's history does.
   This starts the docs workflow:
   fast test set, then `build_reference.py` and `quarto render`
   (a raising code cell or an unresolved link fails the build), then deploy to Pages.
7. Watch for DNS to reach GitHub, then turn on "Enforce HTTPS" once the certificate is issued.
   Set the repo's description and homepage URL.
8. Create `release/0.1.0` from `main`, and start `release.yml` on it. The workflow runs in order:
   1. **Guard:** the branch version, `pyproject.toml` and `CHANGELOG.md` agree,
      and the tag does not exist yet.
   2. **Test:** the heavy set (`pytest --hypothesis-profile=thorough -m ""`)
      on 3.12, 3.13, 3.14 and 3.15, with Graphviz installed.
      The tests that need MuseScore are skipped in CI.
   3. **Build:** `uv build`, then import every module from the wheel on each Python.
   4. **Publish:** to PyPI through the `pypi` environment.
   5. **Record:** tag `v0.1.0` and create the GitHub release from the changelog entry.
9. Verify from outside:
   `pip install openmusickit` in a clean environment gets 0.1.0 and runs a README example,
   the PyPI page renders properly,
   and `https://openmusickit.org` serves the docs, including the API reference and a schema URL.
10. Rename this file to `initial_release.md` (the current name has a typo),
    move it to `_plans/completed/`, commit, and push.
11. Write you a report of what happened, including anything left undone.

### Later releases

Bump the version and changelog on `main`, create `release/X.Y.Z`,
then Actions → Release → Run workflow, choosing that branch.


## If something goes wrong

Claude will not, in order to get a release out:

- edit or skip a test, or drop a Python version from the matrix
- publish with any check failing
- force-push, or change your PyPI or DNS settings

The rules:

- **Test failure:** one re-run, if it looks like a runner problem.
  A simple error may be fixed on `main` and carried into a new run, and will be reported.
  Anything else means no publish, and Claude writes up the failure for you.
- **Publish rejected by PyPI** (usually a publisher field mismatch):
  stops there. Nothing has been published, and you can check the fields and re-run.
- **Docs and PyPI are independent.** A problem with one does not hold up the other.

## Timing

- Repo edits and first docs deploy: about an hour.
- Release workflow: the heavy set took 16 minutes here. Allow 30 to 60 on GitHub's runners.
- **HTTPS on openmusickit.org may take longer than the rest.**
  The parking records have a 6-hour TTL,
  so some resolvers may keep serving the parking page for up to 6 hours after you change them,
  and GitHub cannot issue the certificate until it sees the new records.
  If that is still pending when you return, the site is deployed and only waiting on that.


## Not in this release

Left out on purpose; say if you want any of them:

- a TestPyPI rehearsal (it needs a second account and publisher setup)
- `omk.__version__`
- CI on every push or pull request, or lint and type checks in CI
- content for `CONTRIBUTING.rst`, which is currently empty
- pages at the vocabulary URIs (`https://openmusickit.org/spec/omk` and `/spec/wsmn`),
  which work as identifiers but will return 404 if someone opens them
- the open entries in `_plans/revisit.md`
