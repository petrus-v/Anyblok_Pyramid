# This file is a part of the AnyBlok / Pyramid project
#
#    Copyright (C) 2015 Jean-Sebastien SUZANNE <jssuzanne@anybox.fr>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
from gunicorn.config import Config as GunicornConfig
from gunicorn.app.base import Application
from anyblok.config import Configuration
from anyblok.blok import BlokManager
from anyblok.registry import RegistryManager
from .pyramid_config import Configurator


class Config(GunicornConfig):

    def __init__(self, usage=None, prog=None, configuration_groups=None):
        super(Config, self).__init__(usage=usage, prog=prog)
        self.configuration_groups = configuration_groups

    def parser(self):
        parser = super(Config, self).parser()
        Configuration._load(parser, self.configuration_groups,
                            ('AnyBlok', 'bloks'))
        return parser

    def set(self, name, value):
        if name not in self.settings:
            return  # certainly come from anyblok config

        self.settings[name].set(value)


class WSGIApplication(Application):

    def __init__(self, usage=None, prog=None, configuration_groups=None):
        self.configuration_groups = configuration_groups
        super(WSGIApplication, self).__init__(usage=usage, prog=prog)

    def load_default_config(self):
        self.cfg = Config(self.usage, prog=self.prog,
                          configuration_groups=self.configuration_groups)

    def init(self, parser, opts, args):
        Configuration.parse_options(opts, ('gunicorn',))

        # get the configuration save in AnyBlok configuration in
        # gunicorn configuration
        for name in Configuration.configuration.keys():
            if name in self.cfg.settings:
                value = Configuration.get(name)
                if value:
                    self.cfg.settings[name].set(value)

        BlokManager.load()
        RegistryManager.add_needed_bloks('pyramid')
        dbnames = Configuration.get('db_names', '').split(',')
        dbname = Configuration.get('db_name')
        if dbname not in dbnames:
            dbnames.append(dbname)

        # preload all db names
        for dbname in [x for x in dbnames if x != '']:
            registry = RegistryManager.get(dbname)
            registry.commit()
            registry.session.close()

    def load(self):
        config = Configurator()
        config.include_from_entry_point()
        return config.make_wsgi_app()