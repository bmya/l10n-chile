# -*- coding: utf-8 -*-
from . import sii
from . import partner
from . import account
from . import country
from . import currency
from . import company
from . import invoice


def localization(country):
    def inner(method):
        def call(self, *args, **kwargs):
            _logger.info(args)
            if (self.user != country):
                return False
            else:
                return method(self, *args, **kwargs)
        return call
    return inner
