from django.db import models
from django.utils import timezone

# Create your models here.

class categories(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(categories, on_delete=models.CASCADE)
    description = models.TextField()
    image = models.ImageField(upload_to='product_images/', blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_hot_deal = models.BooleanField(default=False)
    hot_deal_rank = models.PositiveIntegerField(
        default=0,
        help_text='Higher numbers place hot deals ahead of other hot deals.',
    )
    hot_deal_label = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-is_hot_deal', '-hot_deal_rank', '-created_at']
    
    def __str__(self):
        return self.name
