from django.shortcuts import render, get_object_or_404
from django.db.models import Case, IntegerField, Value, When
from market.models import product, categories


def prioritize_products_for_user(products, user):
    priority_category_ids = []
    if user.is_authenticated and hasattr(user, 'profile'):
        priority_category_ids = list(user.profile.priority_categories.values_list('id', flat=True))

    if priority_category_ids:
        products = products.annotate(
            deal_match_rank=Case(
                When(is_hot_deal=True, category_id__in=priority_category_ids, then=Value(2)),
                When(is_hot_deal=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('-deal_match_rank', '-hot_deal_rank', '-created_at')
    else:
        products = products.order_by('-is_hot_deal', '-hot_deal_rank', '-created_at')

    return products


def home(request):
    products = product.objects.select_related('category').filter(is_active=True)
    products = prioritize_products_for_user(products, request.user)
    cats = categories.objects.all()
    return render(request, 'market/home.html', {'products': products, 'categories': cats})


def product_detail(request, pk):
    p = get_object_or_404(product, pk=pk, is_active=True)
    related_products = product.objects.filter(category=p.category, is_active=True).exclude(pk=p.pk)[:4]
    return render(request, 'market/product_detail.html', {'product': p, 'related_products': related_products})


def category_view(request, pk):
    cat = get_object_or_404(categories, pk=pk)
    products = product.objects.filter(category=cat, is_active=True)
    products = prioritize_products_for_user(products, request.user)
    return render(request, 'market/category.html', {'category': cat, 'products': products})


def search(request):
    q = request.GET.get('q', '')
    results = product.objects.filter(name__icontains=q, is_active=True) if q else product.objects.none()
    results = prioritize_products_for_user(results.select_related('category'), request.user)
    return render(request, 'market/home.html', {'products': results, 'categories': categories.objects.all(), 'query': q})
