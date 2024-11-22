# sopel-rtfm

A plugin to suggest documentation links when someone asks a basic question.

## Installing

This plugin is built for Sopel 8.0+.

Releases are hosted on PyPI, so after installing Sopel, all you need is `pip`:

```shell
$ pip install sopel-rtfm
```

### Optional extras

Optionally, you can install `sphobjinv[speedup]` for faster searches; this may
or may not work depending on whether your installation of Python includes the
necessary dependencies for building C extensions.


## Configuring

The easiest way to configure `sopel-rtfm` is via Sopel's configuration
wizard—simply run `sopel-plugins configure rtfm` and enter the values for which
it prompts you.

Two settings exist, one of which is required:

```ini
[rtfm]
# Required: URL of the objects.inv file you want `.rtfm` to search
inventory = https://docs.project.site/objects.inv
# Optional, but useful if automatically determining the base URL doesn't work
link_base = https://docs.project.site/
```

## Using

`sopel-rtfm` provides one command:

* `.rtfm` — searches the configured Sphinx object inventory for the best match,
  and outputs a link to its documentation.
