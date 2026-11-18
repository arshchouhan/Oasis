from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import MarketplaceCartItem, MarketplaceProduct, User


@admin.register(User)
class ClearEyeUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Google sign-in', {'fields': ('google_sub',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('email', 'first_name', 'last_name')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')


@admin.register(MarketplaceProduct)
class MarketplaceProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_active', 'is_featured')
    list_filter = ('category', 'is_active', 'is_featured')
    search_fields = ('name', 'short_description', 'badge')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MarketplaceCartItem)
class MarketplaceCartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'updated_at')
    list_select_related = ('user', 'product')
    search_fields = ('user__username', 'user__email', 'product__name')
