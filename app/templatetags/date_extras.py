from django import template
from datetime import timedelta, datetime

register = template.Library()

@register.filter(name='add_days')
def add_days(value, days):
    """
    Adds (or subtracts) a number of days to a date object.
    Usage: {{ value|add_days:14 }}
    """
    try:
        # Ensure we are working with a datetime object
        # and 'days' is an integer
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        # If input is invalid, return the original value or an empty string
        return value