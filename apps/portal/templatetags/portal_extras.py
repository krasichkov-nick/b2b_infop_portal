from django import template

register = template.Library()


@register.filter
def money(value):
    if value is None:
        return '—'
    try:
        return f'{value:,.2f}'.replace(',', ' ').replace('.00', '')
    except Exception:
        return value


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ''):
            updated.pop(key, None)
        else:
            updated[key] = value
    return updated.urlencode()
