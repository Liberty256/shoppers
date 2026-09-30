from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market.models import categories, product

from .models import CartItem, DeliveryAgent, Order


class ShoppingFlowTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer', password='StrongPass123!')
        category = categories.objects.create(name='Home', description='Home goods')
        self.product = product.objects.create(
            name='Storage basket', price='25.00', category=category,
            description='A useful basket.', stock=5,
        )

    def test_checkout_creates_order_and_reduces_stock(self):
        self.client.force_login(self.customer)
        CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer', 'phone': '0700000000',
            'address': '12 Test Road', 'payment_method': 'cash',
        })
        self.assertRedirects(response, reverse('orders'))
        order = Order.objects.get()
        self.assertEqual(order.customer_name, 'Test Customer')
        self.assertEqual(order.quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(CartItem.objects.filter(user=self.customer).exists())

    def test_cart_cannot_exceed_stock(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('cart_add', args=[self.product.pk]), {'quantity': 9})
        self.assertFalse(CartItem.objects.filter(user=self.customer).exists())

    def test_cart_remove_requires_post(self):
        self.client.force_login(self.customer)
        item = CartItem.objects.create(user=self.customer, product=self.product)
        self.client.get(reverse('cart_remove', args=[item.pk]))
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())


class DeliveryAgentTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('buyer', password='StrongPass123!')
        self.agent_user = User.objects.create_user('driver', password='StrongPass123!')
        self.other_user = User.objects.create_user('other-driver', password='StrongPass123!')
        self.agent = DeliveryAgent.objects.create(user=self.agent_user, phone='0700000001')
        self.other_agent = DeliveryAgent.objects.create(user=self.other_user, phone='0700000002')
        self.order = Order.objects.create(
            user=self.customer, assigned_agent=self.agent, product_name='Parcel',
            quantity=1, total_price='10.00', address='Kampala',
        )

    def test_agent_sees_only_assigned_orders(self):
        Order.objects.create(
            user=self.customer, assigned_agent=self.other_agent,
            product_name='Other parcel', quantity=1, total_price='12.00',
        )
        self.client.force_login(self.agent_user)
        response = self.client.get(reverse('agent_dashboard'))
        self.assertContains(response, 'Parcel')
        self.assertNotContains(response, 'Other parcel')

    def test_agent_can_update_own_order(self):
        self.client.force_login(self.agent_user)
        response = self.client.post(
            reverse('agent_update_order', args=[self.order.pk]), {'state': 'In transit'},
        )
        self.assertRedirects(response, reverse('agent_dashboard'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, 'In transit')

    def test_agent_cannot_update_another_agents_order(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('agent_update_order', args=[self.order.pk]), {'state': 'Delivered'},
        )
        self.assertEqual(response.status_code, 404)
