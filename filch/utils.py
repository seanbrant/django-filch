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


def get_key_value(lookup, value):
    bits = lookup.split('__')
    attr = bits.pop(0)
    if not bits:
        return (attr, value)
    else:
        d = {}
        for i, bit in enumerate(bits):
            if i == len(bits):
                d = {bit: {}}
            else:
                d = {bit: value}
        return (attr, d)
