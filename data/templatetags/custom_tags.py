from django import template


register = template.Library()


@register.filter(name='get_file')
def has_type(file, file_type):
        if file.file_category == file_type:
            return file
        else:
            pass


@register.filter(name='addcss')
def addcss(value, arg):
    css_classes = value.field.widget.attrs.get('class', '').split(' ')
    if css_classes and arg not in css_classes:
        css_classes = '%s %s' % (css_classes, arg)
    return value.as_widget(attrs={'class': css_classes})