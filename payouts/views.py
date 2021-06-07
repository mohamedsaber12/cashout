from django.shortcuts import render


def page_not_found_view(request, exception, **kwargs):
    return render(request, 'error-pages/404.html', status=404)


def error_view(request, **kwargs):
    return render(request, 'error-pages/500.html', status=500)


def permission_denied_view(request, exception, **kwargs):
    return render(request, 'error-pages/403.html', status=403)


def unauthorized_view(request, **kwargs):
    return render(request, 'error-pages/401.html', status=401)


def bad_request_view(request, exception, **kwargs):
    return render(request, 'error-pages/400.html', status=400)


def file_too_large_view(request, exception, **kwargs):
    return render(request, 'error-pages/413.html', status=413)


def no_agent_error_view(request, **kwargs):
    return render(request, 'error-pages/no-agent.html', status=400)
