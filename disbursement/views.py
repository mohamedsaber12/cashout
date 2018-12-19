from django.shortcuts import render


def page_not_found_view(request, **kwargs):
    return render(request, 'error-pages/404.html', status=404)


def error_view(request, **kwargs):
    return render(request, 'error-pages/500.html', status=500)


def permission_denied_view(request, **kwargs):
    return render(request, 'error-pages/403.html', status=403)


def bad_request_view(request, **kwargs):
    return render(request, 'error-pages/400.html', status=400)
