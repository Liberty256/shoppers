from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from clients.models import DeliveryAgent, Order


class AdminAccessTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer', password='StrongPass123!')
        self.staff = User.objects.create_user('staff', password='StrongPass123!', is_staff=True)
        self.superuser = User.objects.create_superuser('owner', 'owner@example.com', 'StrongPass123!')

    def test_only_superusers_can_open_management_dashboard(self):
        for user in (self.customer, self.staff):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_superuser_can_create_agent(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('add_agent'), {
            'username': 'new-driver', 'first_name': 'New', 'last_name': 'Driver',
            'email': 'driver@example.com', 'phone': '0700000003',
            'vehicle_number': 'UBA 123A', 'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('manage_agents'))
        agent = DeliveryAgent.objects.get(user__username='new-driver')
        self.assertEqual(agent.created_by, self.superuser)
        self.assertFalse(agent.user.is_staff)

    def test_assigning_agent_moves_pending_order_to_processing(self):
        agent_user = User.objects.create_user('driver', password='StrongPass123!')
        agent = DeliveryAgent.objects.create(user=agent_user, phone='0700000004')
        order = Order.objects.create(
            user=self.customer, product_name='Parcel', quantity=1, total_price='14.00',
        )
        self.client.force_login(self.superuser)
        self.client.post(reverse('assign_order', args=[order.pk]), {'agent': agent.pk})
        order.refresh_from_db()
        self.assertEqual(order.assigned_agent, agent)
        self.assertEqual(order.state, 'Processing')
