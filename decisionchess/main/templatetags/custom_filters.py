from django import template

register = template.Library()

@register.filter(name='compare')
def compare(name, value):
    return name == value

@register.filter(name='index')
def index(indexable, i):
    return indexable[i]

@register.filter
def slice_list(value, arg):
    """Slices a list based on the argument, e.g., '0:5'."""
    try:
        start, end = map(int, arg.split(':'))
        return value[start:end]
    except (ValueError, TypeError):
        return value  # Return the original list if slicing fails