from django import template

register = template.Library()

@register.filter(name='compare')
def compare(name, value):
    return name == value

@register.filter(name='index')
def index(indexable, i):
    return indexable[i]