from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from market.models import categories, product


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=15, blank=True)
    priority_categories = models.ManyToManyField(
        categories,
        blank=True,
        related_name='interested_customers',
    )

    def __str__(self):
        return self.user.username


class DeliveryAgent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_agent')
    phone = models.CharField(max_length=20)
    vehicle_number = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_delivery_agents',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__first_name', 'user__username']

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_product_per_cart')
        ]


class Order(models.Model):
    STATE_CHOICES = ['Delivered', 'Pending', 'Returned', 'Cancelled', 'Processing', 'In transit']
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_agent = models.ForeignKey(
        DeliveryAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    state = models.CharField(max_length=20, choices=[(c, c) for c in STATE_CHOICES], default='Pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, default='cash')
    order_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    @property
    def status_key(self):
        return self.state.lower().replace(' ', '-')

