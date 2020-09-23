# -*- coding: utf-8 -*-
from django.urls import path

from . import views

app_name = 'kleides_mfa'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('list/', views.DeviceListView.as_view(), name='index'),
    path(
        '<slug:plugin>/create/', views.DeviceCreateView.as_view(),
        name='create'),
    path(
        '<slug:plugin>/update/<path:device_id>/',
        views.DeviceUpdateView.as_view(), name='update'),
    path(
        '<slug:plugin>/verify/<path:device_id>/',
        views.DeviceVerifyView.as_view(), name='verify'),
    path(
        '<slug:plugin>/delete/<path:device_id>/',
        views.DeviceDeleteView.as_view(), name='delete'),
]
