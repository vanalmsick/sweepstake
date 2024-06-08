# -*- coding: utf-8 -*-
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(name="clean_str")
@stringfilter
def clean_str(value):
    """Custom filter to remove ',' and '/' characters from string so it can be used for page URL"""
    return value.replace(",", "/").split("/")[0]
