from django import template

register = template.Library()

@register.filter(name='compare')
def compare(name, value):
    return name == value