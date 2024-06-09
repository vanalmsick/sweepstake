# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.utils.html import mark_safe

register = template.Library()


@register.simple_tag(name="sentry_html")
def sentry_html():
    """Django template tag to import Sentry.io error reporting html head into base.html"""
    return mark_safe(settings.SENTRY_SCRIPT_HEAD)
