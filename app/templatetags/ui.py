from django import template
from django.utils.html import format_html

register = template.Library()

ICONS = {
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2m4 0h2m-8 3h2"/>',
    'chart': '<path d="M4 3v17h17M8 15l4-5 4 2 5-7"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'arrow': '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    'left': '<path d="m14 6-6 6 6 6"/>',
    'right': '<path d="m10 6 6 6-6 6"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    'users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'wallet': '<path d="M20 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h15V8H5a3 3 0 0 1 0-6m15 11h-5v4h5"/>',
    'speaker': '<rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="14" r="4"/><circle cx="12" cy="6" r="1"/>',
    'file': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8m-8 4h5"/>',
    'edit': '<path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15z"/>',
    'trash': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    'download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    'logout': '<path d="M9 4H4v16h5m5-13 5 5-5 5m-7-5h12"/>',
    'menu': '<path d="M4 6h16M4 12h16M4 18h16"/>',
    'close': '<path d="m6 6 12 12M6 18 18 6"/>',
    'filter': '<path d="M4 6h16M7 12h10m-7 6h4"/>',
    'link': '<path d="m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m0 2 1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0" transform="translate(2 1)"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
}

@register.simple_tag
def icon(name):
    from django.utils.safestring import mark_safe
    return format_html('<svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>', mark_safe(ICONS.get(name, ICONS['grid'])))

@register.simple_tag(takes_context=True)
def query_url(context, **changes):
    query = context['request'].GET.copy()
    for key, value in changes.items():
        if value is None or value == '':
            query.pop(key, None)
        else:
            query[key] = value
    return '?' + query.urlencode()
