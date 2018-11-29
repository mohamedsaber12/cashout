from users.models import Brand

def brand_context(request):
    if not request.user.is_authenticated:
        return {}
    brand_qs = Brand.objects.filter(hierarchy=request.user.hierarchy)
    if brand_qs.exists():
        brand = brand_qs.first()
        return {
            'brand_color': brand.color,
            'brand_logo': brand.logo.url
        }
    return {}