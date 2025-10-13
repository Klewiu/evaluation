from django import template

register = template.Library()

@register.filter
def get_item_by_question(queryset, question_id):

    for item in queryset:
        if item.question.id == question_id:
            return item
    return None
