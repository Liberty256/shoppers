from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('orders/', views.manage_orders, name='manage_orders'),
    path('orders/update/<int:pk>/', views.update_order_status, name='update_order_status'),
    path('orders/<int:pk>/assign/', views.assign_order, name='assign_order'),
    path('products/', views.products, name='manage_products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('categories/', views.categories_view, name='manage_categories'),
    path('agents/', views.agents, name='manage_agents'),
    path('agents/add/', views.add_agent, name='add_agent'),
    path('agents/<int:pk>/toggle/', views.toggle_agent, name='toggle_agent'),
]
