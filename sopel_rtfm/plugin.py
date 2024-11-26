"""sopel-rtfm

A plugin to suggest documentation links when someone asks a basic question.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from urllib.error import URLError

import sphobjinv
from sphobjinv.error import SphobjinvError

from sopel import plugin, tools
from sopel.config import types


LOGGER = tools.get_logger('rtfm')


class RTFMSection(types.StaticSection):
    inventory = types.ValidatedAttribute('inventory', default=types.NO_DEFAULT)
    """URL to the target Sphinx object inventory (``.inv`` file)."""

    link_base = types.ValidatedAttribute('link_base')
    """Base URL for links to objects.

    Only required if automatic detection does not work properly.

    Trailing slash is expected.
    """


def configure(config):
    config.define_section('rtfm', RTFMSection, validate=False)
    config.rtfm.configure_setting(
        'inventory',
        "Enter the URL of your project's objects.inv file:",
    )
    config.rtfm.configure_setting(
        'link_base',
        "Enter the base URL of your documentation (leave blank for automatic detection):"
    )


def setup(bot):
    bot.config.define_section('rtfm', RTFMSection)

    LOGGER.info('Inventory URL: %s', bot.config.rtfm.inventory)
    if not bot.config.rtfm.inventory.endswith('.inv'):
        LOGGER.warning(
            'Inventory URL does not end with `.inv`; this may be incorrect.'
        )

    rtfm_base = bot.config.rtfm.link_base
    if not rtfm_base:
        LOGGER.info(
            'No `link_base` set; assuming base URL from `inventory` setting.')
        # `dirname()` never includes a trailing slash unless you pass it '/',
        # and '/' by itself isn't a valid URL. Appending the trailing slash here
        # eliminates log noise from the check below when the user hasn't
        # configured `link_base` manually.
        rtfm_base = os.path.dirname(bot.config.rtfm.inventory) + '/'

    if not rtfm_base.endswith('/'):
        LOGGER.info(
            'Base URL %r has no trailing slash; adding one.', rtfm_base)
        rtfm_base += '/'

    bot.memory['rtfm_base'] = rtfm_base
    LOGGER.info('Base URL for RTFM links: %s', rtfm_base)

    update_sphinx_objects(bot)


@plugin.interval(3600)
def update_sphinx_objects(bot, force=False):
    now = datetime.now(timezone.utc)
    age = now - bot.memory.get('rtfm_cache_time',
                               datetime.fromtimestamp(0, timezone.utc))

    if not force and age.total_seconds() < 86400:  # 1 day / 24 hours in seconds
        LOGGER.debug("Inventory cache is under one day old, skipping update.")
        return

    LOGGER.debug("Beginning inventory cache update.")

    try:
        inv = sphobjinv.Inventory(url=bot.config.rtfm.inventory)
    except ValueError:
        # invalid URL, probably
        LOGGER.error(
            'Could not fetch inventory file; URL seems to be malformed: %s',
            bot.config.rtfm.inventory,
        )
        return
    except (SphobjinvError, URLError) as e:
        # couldn't fetch due to urllib error or unrecognized file format
        LOGGER.error(
            'Could not fetch inventory file from %r: %s',
            bot.config.rtfm.inventory, str(e),
        )
        return

    objects = {
        name: url
        for (name, url) in [
            (
                o.as_rst,
                o.uri_expanded,
            )
            for o in inv.objects
        ]
    }

    bot.memory['rtfm_inventory'] = inv
    bot.memory['rtfm_objects'] = objects
    bot.memory['rtfm_cache_time'] = now

    LOGGER.debug("Finished updating inventory cache.")


def shutdown(bot):
    for key in ['rtfm_base', 'rtfm_inventory', 'rtfm_objects']:
        try:
            del bot.memory[key]
        except KeyError:
            pass


@plugin.commands('rtfm', 'docs')
@plugin.example('.rtfm bind_host')
@plugin.output_prefix('[rtfm] ')
def suggest_doc_link(bot, trigger):
    """Search the configured Sphinx object inventory and output a link to the best match."""
    query = trigger.group(2)

    if not query:
        bot.say(bot.memory['rtfm_base'])
        return

    results = bot.memory['rtfm_inventory'].suggest(query, thresh=85)

    if not results:
        bot.say("No result found for query: {}".format(query))
        return

    docs = []
    sections = []
    modules = []
    classes = []
    functions = []
    other = []
    for r in results:
        # This is a lazy way to order the results so that "bigger" or more
        # important objects are returned first
        if ':doc:' in r:
            docs.append(r)
        elif ':label:' in r:
            sections.append(r)
        elif ':module:' in r:
            modules.append(r)
        elif ':class:' in r:
            classes.append(r)
        elif ':func:' in r or ':method:' in r:
            functions.append(r)
        else:
            other.append(r)

    results = docs + sections + modules + classes + functions + other

    bot.say(bot.memory['rtfm_base'] + bot.memory['rtfm_objects'][results[0]])


@plugin.commands('rtfmupdate')
@plugin.require_admin
def force_update(bot, trigger):
    """Force an update of the target Sphinx object inventory.

    In lieu of restarting the bot or waiting for the next automatic refresh
    (every 24 hours), a bot admin can force an immediate update.
    """
    bot.reply("Attempting to update Sphinx objects.")
    update_sphinx_objects(bot, force=True)
