# -*- coding: utf-8 -*-
from django import template

register = template.Library()


@register.filter(name="st_nd_rd_th")
def st_nd_rd_th(value):
    """Custom filter to add st, nd, rd, th to numbers"""
    str_value = str(value)
    exception_case = any([str_value == i for i in ["11", "12", "13"]])
    if exception_case:
        return "th"
    elif str_value[-1:] == "1":
        return "st"
    elif str_value[-1:] == "2":
        return "nd"
    elif str_value[-1:] == "3":
        return "rd"
    elif str_value[-1:].isdigit() is False:
        return ""
    else:
        return "th"
