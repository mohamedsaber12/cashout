from users.models import Brand

def brand_context(request):
    if not request.user.is_authenticated:
        return {}
    brand = request.user.brand
    if brand is not None:
        return {
             'brand_color': brand.color,
             'brand_logo': brand.logo.url
        }
       
    return {}


def current_status(request):
    """return value is disbursement or collection"""
    if not request.user.is_authenticated:
        return {}
    print(request.user.get_status(request))
    return {'current_status': request.user.get_status(request)}
