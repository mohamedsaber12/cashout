from django import template


register = template.Library()


@register.filter(name='get_file')
def has_type(file, file_type):
        if file.file_category == file_type:
            return file
        else:
            pass


@register.filter(name='add_class')
@register.filter
def add_class(field, class_name):
    return field.as_widget(attrs={
        "class": " ".join((field.css_classes(), class_name))
    })