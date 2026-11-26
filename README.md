# link-checker

A small local tool. It reads the Markdown files of a folder and reports broken internal links, missing illustrations and missing heading anchors. It
makes no network call: a link to a web address is left alone. It writes nothing.

Status: the spec and the tests are written first (SPEC.md and tests/). The code does not exist yet; the tests fail until it does.

    python3 -m linkcheck ROOT --paths site/tech docs/plans
