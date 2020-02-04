from django import template


register = template.Library()


@register.filter(name='get_file')
def has_type(file, name):
        if file.file_category == name:
            return file
        else:
            pass


@register.filter(name='add_class')
@register.filter
def add_class(field, class_name):
    return field.as_widget(attrs={
        "class": " ".join((field.css_classes(), class_name))
    })


@register.filter(name='invert_dir')
def invert_dir(dir, language_code):
        if language_code == 'en':
            return dir
        if dir == 'left':
            return 'right'
        return 'left'
