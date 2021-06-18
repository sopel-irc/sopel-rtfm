# coding=utf8
"""sopel-rtfm

A plugin to suggest documentation links when someone asks a basic question.
"""
from __future__ import unicode_literals, absolute_import, division, print_function

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

    try:
        inv = sphobjinv.Inventory(url=bot.config.rtfm.inventory)
    except ValueError:
        # invalid URL, probably
        LOGGER.error(
            'Could not fetch inventory file; URL seems to be malformed: %s',
            bot.config.rtfm.inventory,
        )
        raise
    except (SphobjinvError, URLError) as e:
        # couldn't fetch due to urllib error or unrecognized file format
        LOGGER.error(
            'Could not fetch inventory file: %s',
            str(e),
        )
        raise

    objects = {
        name: url
        for (name, url) in [
            (
                ':{domain}:{role}:`{name}`'.format(
                    domain=o.domain,
                    role=o.role,
                    name=o.name,
                ),
                o.uri_expanded,
            )
            for o in inv.objects
        ]
    }

    bot.memory['rtfm_base'] = (
        bot.config.rtfm.link_base or
        os.path.dirname(bot.config.rtfm.inventory)
    )
    bot.memory['rtfm_inventory'] = inv
    bot.memory['rtfm_objects'] = objects

    if not bot.memory['rtfm_base'].endswith('/'):
        bot.memory['rtfm_base'] += '/'


def shutdown(bot):
    for key in ['rtfm_base', 'rtfm_inventory', 'rtfm_objects']:
        try:
            del bot.memory[key]
        except KeyError:
            pass


@module.commands('rtfm')
@module.output_prefix('[rtfm] ')
def suggest_doc_link(bot, trigger):
    query = trigger.group(2)

    if not query:
        bot.say(bot.memory['rtfm_base'])
        return

    try:
        result = bot.memory['rtfm_inventory'].suggest(query, thresh=75)[0]
    except (IndexError, TypeError):
        bot.say("No result found for query: {}".format(query))
        return

    link = bot.memory['rtfm_base'] + bot.memory['rtfm_objects'][result]

    bot.say(link)
