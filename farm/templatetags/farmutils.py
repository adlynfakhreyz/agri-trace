from django import template

register = template.Library()

@register.filter
def divisible(value, arg):
    """Returns the result of value divided by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Returns the result of value multiplied by arg"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0