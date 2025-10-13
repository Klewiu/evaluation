from django import template

register = template.Library()

@register.filter
def dict_get_item(dictionary, key):
    return dictionary.get(key)