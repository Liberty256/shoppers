from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from clients.models import DeliveryAgent, Order
from market.models import categories, product

from .forms import AgentCreationForm, CategoryForm, ProductForm


superuser_required = user_passes_test(lambda user: user.is_superuser, login_url='/clients/login/')


@superuser_required
def dashboard(request):
    active_orders = Order.objects.exclude(state__in=['Delivered', 'Cancelled', 'Returned'])
    context = {
        'total_customers': User.objects.filter(is_superuser=False, delivery_agent__isnull=True).count(),
        'total_products': product.objects.filter(is_active=True).count(),
        'total_orders': Order.objects.count(),
        'total_revenue': Order.objects.filter(state='Delivered').aggregate(r=Sum('total_price'))['r'] or 0,
        'unassigned_orders': active_orders.filter(assigned_agent__isnull=True).count(),
        'active_agents': DeliveryAgent.objects.filter(is_active=True).count(),
        'recent_orders': Order.objects.select_related('user', 'assigned_agent__user')[:6],
        'recent_products': product.objects.select_related('category')[:6],
    }
    return render(request, 'admin_panel/dashboard.html', context)


@superuser_required
def manage_orders(request):
    orders = Order.objects.select_related('user', 'assigned_agent__user')
    query = request.GET.get('q', '').strip()
    state = request.GET.get('state', '').strip()
    if query:
        orders = orders.filter(
            Q(user__username__icontains=query)
            | Q(customer_name__icontains=query)
            | Q(product_name__icontains=query)
            | Q(id__icontains=query)
        )
    if state in Order.STATE_CHOICES:
        orders = orders.filter(state=state)
    context = {
        'orders': orders,
        'agents': DeliveryAgent.objects.filter(is_active=True).select_related('user'),
        'states': Order.STATE_CHOICES,
        'query': query,
        'selected_state': state,
    }
    return render(request, 'admin_panel/orders.html', context)


@superuser_required
def update_order_status(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        state = request.POST.get('state')
        if state in Order.STATE_CHOICES:
            order.state = state
            order.updated_at = timezone.now()
            order.save(update_fields=['state', 'updated_at'])
            messages.success(request, f'Order #{order.pk} status updated.')
    return redirect('manage_orders')


@superuser_required
def assign_order(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        agent_id = request.POST.get('agent')
        order.assigned_agent = (
            get_object_or_404(DeliveryAgent, pk=agent_id, is_active=True) if agent_id else None
        )
        if order.assigned_agent and order.state == 'Pending':
            order.state = 'Processing'
        order.updated_at = timezone.now()
        order.save(update_fields=['assigned_agent', 'state', 'updated_at'])
        messages.success(request, f'Delivery assignment for order #{order.pk} updated.')
    return redirect('manage_orders')


@superuser_required
def products(request):
    products_list = product.objects.select_related('category')
    return render(request, 'admin_panel/products.html', {'products': products_list})


@superuser_required
def add_product(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product added to the storefront.')
        return redirect('manage_products')
    return render(request, 'admin_panel/product_form.html', {'form': form})


@superuser_required
def edit_product(request, pk):
    selected_product = get_object_or_404(product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=selected_product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product changes saved.')
        return redirect('manage_products')
    return render(
        request,
        'admin_panel/product_form.html',
        {'form': form, 'product': selected_product},
    )


@superuser_required
def categories_view(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category created.')
        return redirect('manage_categories')
    return render(
        request,
        'admin_panel/categories.html',
        {'form': form, 'categories': categories.objects.all()},
    )


@superuser_required
def agents(request):
    return render(
        request,
        'admin_panel/agents.html',
        {'agents': DeliveryAgent.objects.select_related('user').annotate(order_total=Sum('orders__quantity'))},
    )


@superuser_required
def add_agent(request):
    form = AgentCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save(created_by=request.user)
        messages.success(request, 'Delivery agent account created.')
        return redirect('manage_agents')
    return render(request, 'admin_panel/agent_form.html', {'form': form})


@superuser_required
def toggle_agent(request, pk):
    if request.method == 'POST':
        agent = get_object_or_404(DeliveryAgent, pk=pk)
        agent.is_active = not agent.is_active
        agent.user.is_active = agent.is_active
        agent.save(update_fields=['is_active'])
        agent.user.save(update_fields=['is_active'])
        state = 'activated' if agent.is_active else 'deactivated'
        messages.success(request, f'{agent} has been {state}.')
    return redirect('manage_agents')
