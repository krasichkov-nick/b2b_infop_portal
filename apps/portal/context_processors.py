from .cart import SessionCart


def portal_context(request):
    cart = SessionCart(request)
    profile = getattr(getattr(request, 'user', None), 'company_profile', None)
    return {
        'portal_cart_count': cart.count(),
        'portal_company': getattr(profile, 'company', None),
    }
