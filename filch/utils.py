from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.utils import simplejson


class JSONEncoder(simplejson.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        return super(JSONEncoder, self).default(self, obj)


def dumps(value):
    return JSONEncoder().encode(value)


def loads(s):
    value = simplejson.loads(s, parse_float=Decimal,
        encoding=settings.DEFAULT_CHARSET)
    return value


class DotDict(dict):

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, attr):
        return self.get(attr, None)


def convert_lookup_to_dict(key, value):
    # key that might look like this:
    # key = 'location__city__name'
    # value = 'Chicago'
    # and returns this:
    # ('location', {'city': 'Chicago'})
    bits = key.split("__")
    k = bits.pop(0)
    v = {}
    if not bits:
        return (k, value)
    while bits:
        bit = bits.pop()
        if not v:
            v = {bit: value}
        else:
            v = {bit: v}
    return (k, DotDict(v))
