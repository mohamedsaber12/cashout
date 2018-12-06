from django.contrib.auth.decorators import login_required
from django.views.static import serve

@login_required
def protected_media_serve(request, path, document_root=None, show_indexes=False):
    return serve(request, path, document_root, show_indexes)
