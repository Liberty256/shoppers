from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from market.models import product

from .forms import CheckoutForm, CustomerRegistrationForm
from .models import CartItem, Order


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome to Shoppers. Your account is ready.')
        return redirect('home')
    return render(request, 'clients/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_for_role(request.user)
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username', '').strip(),
            password=request.POST.get('password', ''),
        )
        if user:
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect_for_role(user)
        messages.error(request, 'The username or password is incorrect.')
    return render(request, 'clients/login.html', {'next': next_url})


def redirect_for_role(user):
    if user.is_superuser:
        return redirect('dashboard')
    if hasattr(user, 'delivery_agent') and user.delivery_agent.is_active:
        return redirect('agent_dashboard')
    return redirect('home')


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been signed out.')
        return redirect('home')
    return redirect('home')


@login_required
def cart_view(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum(item.subtotal for item in items)
    return render(request, 'clients/cart.html', {'cart_items': items, 'total': total})


@login_required
def cart_add(request, pk):
    if request.method != 'POST':
        return redirect('product_detail', pk=pk)
    selected_product = get_object_or_404(product, pk=pk, is_active=True)
    try:
        quantity = max(1, min(int(request.POST.get('quantity', 1)), 99))
    except (TypeError, ValueError):
        quantity = 1
    item, created = CartItem.objects.get_or_create(user=request.user, product=selected_product)
    desired_quantity = quantity if created else item.quantity + quantity
    if selected_product.stock < desired_quantity:
        if created:
            item.delete()
        messages.error(request, f'Only {selected_product.stock} units are currently available.')
    else:
        item.quantity = desired_quantity
        item.save()
        messages.success(request, f'{selected_product.name} was added to your cart.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))


@login_required
def cart_update(request, pk):
    item = get_object_or_404(CartItem.objects.select_related('product'), pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            quantity = max(1, min(int(request.POST.get('quantity', 1)), 99))
        except (TypeError, ValueError):
            quantity = 1
        if quantity > item.product.stock:
            messages.error(request, f'Only {item.product.stock} units are available.')
        else:
            item.quantity = quantity
            item.save(update_fields=['quantity'])
    return redirect('cart')


@login_required
def cart_remove(request, pk):
    if request.method == 'POST':
        CartItem.objects.filter(pk=pk, user=request.user).delete()
        messages.success(request, 'Item removed from your cart.')
    return redirect('cart')


@login_required
def checkout_view(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')
    if not items.exists():
        messages.info(request, 'Your cart is empty.')
        return redirect('cart')
    total = sum(item.subtotal for item in items)
    initial = {
        'full_name': request.user.get_full_name() or request.user.username,
        'phone': getattr(getattr(request.user, 'profile', None), 'contact', ''),
    }
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                locked_products = {
                    item.pk: item
                    for item in product.objects.select_for_update().filter(
                        pk__in=[cart_item.product_id for cart_item in items]
                    )
                }
                for cart_item in items:
                    selected_product = locked_products[cart_item.product_id]
                    if not selected_product.is_active or selected_product.stock < cart_item.quantity:
                        raise ValueError(
                            f'{selected_product.name} no longer has enough stock for this order.'
                        )
                for cart_item in items:
                    selected_product = locked_products[cart_item.product_id]
                    Order.objects.create(
                        user=request.user,
                        product_name=selected_product.name,
                        quantity=cart_item.quantity,
                        total_price=cart_item.subtotal,
                        customer_name=form.cleaned_data['full_name'],
                        phone=form.cleaned_data['phone'],
                        address=form.cleaned_data['address'],
                        payment_method=form.cleaned_data['payment_method'],
                    )
                    selected_product.stock -= cart_item.quantity
                    selected_product.save(update_fields=['stock'])
                items.delete()
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, 'Order placed successfully. We will keep you updated here.')
            return redirect('orders')
    return render(request, 'clients/checkout.html', {'cart_items': items, 'total': total, 'form': form})


@login_required
def orders_view(request):
    orders = Order.objects.filter(user=request.user).select_related('assigned_agent')
    return render(request, 'clients/orders.html', {'orders': orders})


def _is_active_agent(user):
    return (
        user.is_authenticated
        and hasattr(user, 'delivery_agent')
        and user.delivery_agent.is_active
    )


@user_passes_test(_is_active_agent, login_url='/clients/login/')
def agent_dashboard(request):
    agent = request.user.delivery_agent
    orders = agent.orders.select_related('user').exclude(state='Cancelled')
    context = {
        'agent': agent,
        'orders': orders,
        'active_count': orders.exclude(state__in=['Delivered', 'Returned']).count(),
        'delivered_count': orders.filter(state='Delivered').count(),
        'in_transit_count': orders.filter(state='In transit').count(),
    }
    return render(request, 'agents/dashboard.html', context)


@user_passes_test(_is_active_agent, login_url='/clients/login/')
def agent_update_order(request, pk):
    if request.method != 'POST':
        return redirect('agent_dashboard')
    order = get_object_or_404(Order, pk=pk, assigned_agent=request.user.delivery_agent)
    allowed_states = {'Processing', 'In transit', 'Delivered', 'Returned'}
    new_state = request.POST.get('state')
    if new_state in allowed_states:
        order.state = new_state
        order.updated_at = timezone.now()
        order.save(update_fields=['state', 'updated_at'])
        messages.success(request, f'Order #{order.pk} marked {new_state.lower()}.')
    else:
        messages.error(request, 'That delivery status is not allowed.')
    return redirect('agent_dashboard')
