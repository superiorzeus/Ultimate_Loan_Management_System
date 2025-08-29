from django import template
import locale

register = template.Library()

@register.filter
def format_currency(value):
    try:
        return "GH₵{:,.2f}".format(float(value))
    except (ValueError, locale.Error):
        # Fallback in case of locale setting issues
        return value