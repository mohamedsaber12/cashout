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
