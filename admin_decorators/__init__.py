# -*- coding: utf-8 -*-
from __future__ import absolute_import
from urllib import urlencode, splitquery
from functools import wraps
from django.utils.safestring import mark_safe
from django.utils import six
from django.template import Template, Context
from django.core.urlresolvers import reverse

try:
    from django.template.defaultfilters import truncatechars as _truncatechars
except ImportError: # django < 1.4
    def _truncatechars(string, max_len):
        # simple fallback
        dots = '...'
        assert max_len > len(dots)
        if len(string) < max_len:
            return string
        return string[:(max_len-len(dots))]+dots

def short_description(description):
    """
    Sets 'short_description' attribute (this attribute is used by list_display).
    """
    def decorator(func):
        func.short_description = description
        return func
    return decorator

def order_field(field):
    """
    Sets 'admin_order_field' attribute (this attribute is used by list_display).
    """
    def decorator(func):
        func.admin_order_field = field
        return func
    return decorator

def allow_tags(func):
    """
    Unified 'allow_tags' that works both for list_display and readonly_fields.
    """
    @wraps(func)
    def inner(*args, **kwargs):
        res = func(*args, **kwargs)
        return mark_safe(res)

    inner.allow_tags = True
    return inner

def boolean(func):
    """
    Sets 'boolean' attribute (this attribute is used by list_display).
    """
    func.boolean=True
    return func

def limit_width(max_len):
    """
    Truncates the decorated function's result if it is longer than max_length.
    """
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            res = func(*args, **kwargs)
            return _truncatechars(res, max_len)
        return inner
    return decorator

def list_decorator(short_description=None, order_field=None, allow_tags=None, boolean=None):
    def decorator(func):
        if short_description is not None:
            func.short_description = short_description
        if order_field is not None:
            func.admin_order_field = order_field
        if allow_tags is not None:
            func.allow_tags = allow_tags
        if boolean is not None:
            func.boolean = boolean
        return func
    return decorator

def format_output(template_string):
    """
    Formats the value according to template_string using django's Template.
    Example::

        @allow_tags
        @format_output('{{ value|urlize }}')
        def object_url(self, obj):
            return obj.url

    """

    tpl = Template(template_string)

    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            res = func(*args, **kwargs)
            return tpl.render(Context({'value': res}))
        return inner
    return decorator


def apply_filter(filter_string):
    """
    Applies django template filter to output.
    Example::

        @apply_filter('truncatewords:2')
        def object_description(self, obj):
            return obj.description

    """
    def decorator(func):
        template_string = "{{ value|%s }}" % filter_string
        return format_output(template_string)(func)
    return decorator

def external_url(func):
    """
    Example::

        @external_url
        def github_project(self, obj):
            return 'http://github.com/{}'.format(obj.project)
    """
    template = "<a href='{{ value }}' target='_blank'>{{ value }}</a>"
    return allow_tags(format_output(template)(func))

def admin_url(viewname, displaytext=None):
    """
    Example::

        @url('admin:app_model_chagelist')
        def filter(self, obj):
            return {'relation__exact__id': obj.relation.id}
    """
    keys = ('viewname', 'urlconf', 'args', 'kwargs', 'current_app')

    def decorator(func):

        @wraps(func)
        def inner(*args, **kwargs):
            res = func(*args, **kwargs)
            args = dict((k, res[k]) for k in keys if k in res)
            if viewname not in args:
                args['viewname'] = viewname
            url = reverse(**args)
            querystring = urlencode(dict((k, v) for k, v in six.iteritems(res) if k not in args))
            if querystring:
                path, qs = splitquery(url)
                if qs:
                    querystring = qs + '&' + querystring
                if path:
                    url = '{}?{}'.format(path, querystring)
                else:
                    url = '/?' + querystring
            return u"<a href='{}'>{}</a>".format(url, displaytext if displaytext is not None else url)
        return allow_tags(inner)
    return decorator
