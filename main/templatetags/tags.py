from django import template
from django.utils.html import escape

register = template.Library()


@register.filter(name='safe_escape')
def safe_escape(value):
    return escape(value)
