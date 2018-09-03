from django import template


register = template.Library()


@register.filter(name='get_file')
def has_type(file, file_type):
        if file.file_category == file_type:
            return file
        else:
            pass
