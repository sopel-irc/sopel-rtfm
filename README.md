# sopel-rtfm

A plugin to suggest documentation links when someone asks a basic question.

## Functions

`sopel-rtfm` provides one command:

* `.rtfm` — searches the configured Sphinx object inventory for the best
  match, and outputs a link to its documentation.

## Configuration

Two settings exist, one of which is required:

```ini
[rtfm]
# Required: URL of the objects.inv file you want `.rtfm` to search
inventory = https://docs.project.site/objects.inv
# Optional, but useful if automatically determining the base URL doesn't work
link_base = https://docs.project.site/
```

## Requirements

This plugin is built for Sopel 7.0+, but targets Python 3.6+ only (no py2.7).

In addition, it needs the `sphobjinv` module from PyPI.

Optionally, you can install `sphobjinv[speedup]` for faster searches; this may
or may not work depending on whether your installation of Python includes the
necessary dependencies for building C extensions.
