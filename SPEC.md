# Spec: link-checker (tests first)

## Purpose

Find, in a tree of Markdown files, the links that point at something that is not there: a file that does not exist, an illustration that does not
exist, a heading anchor that does not exist. Standard library Python 3.10 or later. No network, nothing written.

## What it reads

Every `*.md` file under the folders given with `--paths` (each relative to `ROOT`; default: all of `ROOT`). A link is `[text](target)`; an illustration is
`![alt](target)`. It skips fenced code blocks (triple backticks or `~~~`) and inline code (backticks), where a link is only an example.

## What it checks

- **External targets** (`http://`, `https://`, `mailto:`, `tel:`, any `scheme:`) are NOT checked and never fetched.
- **A file target** (`other.md`, `../img/a.png`, `sub/page.md#heading`) is resolved relative to the folder of the file that holds the link. The query
  (`?x=1`) is dropped and percent-encoding is decoded (`my%20file.md`). It is a problem when the file does not exist: `broken link` for a link, `missing
  illustration` for an image.
- **An anchor** (`#heading`, or `page.md#heading` where the file exists) is a problem when the target file has no heading with that anchor: `missing anchor`.
  An anchor is the GitHub kind: the heading text lowercased, anything that is not a letter, a digit, a space or a hyphen removed, spaces turned into hyphens;
  a second heading with the same text gets `-1`, a third `-2`.
- A target that leaves `ROOT` (`../../../etc/passwd`) is a problem `outside the folder`, whether or not the file exists, and is never opened.
- A link with an empty target `[x]()` is a problem `empty link`.

## The functions (package `linkcheck`)

- `anchors(text) -> set[str]`: the anchors of a Markdown text.
- `extract_links(text) -> list[Link]`: `Link` has `line` (1-based), `target`, `is_image`. Code is skipped.
- `check_tree(root, paths=None) -> list[Problem]`: `Problem` has `path` (relative to `root`, with `/`), `line`, `kind`, `target`. Sorted by path, then line.

## The command

`python3 -m linkcheck ROOT [--paths P ...]`. One line per problem on standard output, `PATH:LINE: KIND: TARGET`, and then `N problem(s).`; with none it prints
`No problems.`. Exit 0 when there is no problem, 1 when there is at least one, 2 for a bad argument or a ROOT that is not a folder (one line `error: ...` on
standard error, no traceback).

## Rules that never bend

- No network. Nothing is written. A file outside ROOT is never opened.

## Decisions log

- 2026-11-25: spec and tests first, written by the builder; the code is built later with Kiro doing real work in it (G-0054).

## Open questions

- Should it also check that a link's text is not empty, or that an image has alt text? Recommendation: no, keep it to things that are missing.
