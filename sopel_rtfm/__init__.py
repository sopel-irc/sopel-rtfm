# coding=utf8
"""sopel-rtfm

A plugin to suggest documentation links when someone asks a basic question.
"""
from __future__ import unicode_literals, absolute_import, division, print_function

from datetime import datetime
import os
from urllib.error import URLError
from urllib.parse import urlparse

import sphobjinv
from sphobjinv.error import SphobjinvError

from sopel import module, tools
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
        "Enter the URL of your project's objects.inv file.",
    )
    config.rtfm.configure_setting(
        'link_base',
        "Enter the base URL of your documentation (leave blank for automatic detection)."
    )


def setup(bot):
    bot.config.define_section('rtfm', RTFMSection)

    bot.memory['rtfm_base'] = (
        bot.config.rtfm.link_base or
        os.path.dirname(bot.config.rtfm.inventory)
    )

    if not bot.memory['rtfm_base'].endswith('/'):
        bot.memory['rtfm_base'] += '/'

    update_sphinx_objects(bot)


@module.interval(3600)
def update_sphinx_objects(bot, force=False):
    now = datetime.utcnow()
    age = now - bot.memory.get('rtfm_cache_time', datetime.fromtimestamp(0))

    if not force and age.total_seconds() < 86400:  # 1 day / 24 hours in seconds
        LOGGER.debug("Inventory cache is under one day old, skipping update.")
        return

    LOGGER.debug("Beginning inventory cache update.")

    try:
        inv = sphobjinv.Inventory(url=bot.config.rtfm.inventory)
    except ValueError:
        # invalid URL, probably
        LOGGER.exception(
            'Could not fetch inventory file; URL seems to be malformed: %s',
            bot.config.rtfm.inventory,
        )
        return
    except (SphobjinvError, URLError) as e:
        # couldn't fetch due to urllib error or unrecognized file format
        LOGGER.exception(
            'Could not fetch inventory file: %s',
            str(e),
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


@module.commands('rtfm')
@module.example('.rtfm bind_host')
@module.output_prefix('[rtfm] ')
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


@module.commands('rtfmupdate')
@module.require_admin
def force_update(bot, trigger):
    """Force an update of the target Sphinx object inventory.

    In lieu of restarting the bot or waiting for the next automatic refresh
    (every 24 hours), a bot admin can force an immediate update.
    """
    bot.reply("Attempting to update Sphinx objects.")
    update_sphinx_objects(bot, force=True)
