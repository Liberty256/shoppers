from django.contrib.auth.models import User
from django.test import TestCase

from clients.models import Profile

from .models import categories, product
from .views import prioritize_products_for_user


class ProductPriorityTests(TestCase):
    def test_priority_category_hot_deals_are_listed_first(self):
        home = categories.objects.create(name='Home', description='Home goods')
        tech = categories.objects.create(name='Tech', description='Tech goods')
        user = User.objects.create_user('customer', password='StrongPass123!')
        profile = Profile.objects.create(user=user, contact='0700000000')
        profile.priority_categories.add(tech)

        normal_priority = product.objects.create(
            name='Normal tech product',
            price='20.00',
            category=tech,
            description='A regular item.',
            stock=8,
        )
        other_hot_deal = product.objects.create(
            name='Home hot deal',
            price='15.00',
            category=home,
            description='A good home deal.',
            stock=8,
            is_hot_deal=True,
            hot_deal_rank=99,
        )
        priority_hot_deal = product.objects.create(
            name='Tech hot deal',
            price='30.00',
            category=tech,
            description='A good tech deal.',
            stock=8,
            is_hot_deal=True,
        )

        products = prioritize_products_for_user(product.objects.all(), user)

        self.assertEqual(
            list(products.values_list('id', flat=True)),
            [priority_hot_deal.id, other_hot_deal.id, normal_priority.id],
        )
