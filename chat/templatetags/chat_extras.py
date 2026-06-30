from django import template

register = template.Library()


@register.filter
def format_label(value: str) -> str:
    from chat.constants import FORMAT_LABELS

    return FORMAT_LABELS.get(value, value)
