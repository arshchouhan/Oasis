from decimal import Decimal

import razorpay
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import MarketplaceCartItem, MarketplaceProduct


def _patient_only(request):
    return request.user.account_type == request.user.AccountType.PATIENT


def _razorpay_test_configured():
    return (
        settings.RAZORPAY_KEY_ID.startswith('rzp_test_')
        and bool(settings.RAZORPAY_KEY_SECRET)
    )


def _cart_context(user):
    items = list(
        MarketplaceCartItem.objects.filter(user=user)
        .select_related('product')
        .filter(product__is_active=True)
    )
    total = sum((item.product.price * item.quantity for item in items), Decimal('0.00'))
    return {'cart_items': items, 'cart_total': total, 'cart_count': sum(item.quantity for item in items)}


@login_required(login_url='login')
def marketplace(request):
    if not _patient_only(request):
        return redirect('doctor_dashboard')
    category = request.GET.get('category', '')
    products = MarketplaceProduct.objects.filter(is_active=True)
    if category in MarketplaceProduct.Category.values:
        products = products.filter(category=category)
    context = {
        'products': products,
        'categories': MarketplaceProduct.Category.choices,
        'active_category': category,
        **_cart_context(request.user),
    }
    return render(request, 'patient_portal/marketplace.html', context)


@login_required(login_url='login')
@require_POST
def cart_add(request, product_id):
    if not _patient_only(request):
        return HttpResponseBadRequest('Marketplace is only available in the patient portal.')
    product = get_object_or_404(MarketplaceProduct, pk=product_id, is_active=True)
    item, created = MarketplaceCartItem.objects.get_or_create(user=request.user, product=product)
    if not created and item.quantity < product.stock:
        item.quantity = F('quantity') + 1
        item.save(update_fields=('quantity', 'updated_at'))
    elif created and product.stock == 0:
        item.delete()
        messages.error(request, f'{product.name} is currently out of stock.')
        return redirect('marketplace')
    messages.success(request, f'{product.name} was added to your basket.')
    return redirect(request.POST.get('next') or 'marketplace')


@login_required(login_url='login')
@require_POST
def cart_update(request, item_id):
    if not _patient_only(request):
        return HttpResponseBadRequest('Marketplace is only available in the patient portal.')
    item = get_object_or_404(MarketplaceCartItem, pk=item_id, user=request.user)
    action = request.POST.get('action')
    if action == 'increase' and item.quantity < item.product.stock:
        item.quantity = F('quantity') + 1
        item.save(update_fields=('quantity', 'updated_at'))
    elif action == 'decrease' and item.quantity > 1:
        item.quantity = F('quantity') - 1
        item.save(update_fields=('quantity', 'updated_at'))
    elif action == 'remove':
        item.delete()
    else:
        messages.info(request, 'That quantity cannot be updated.')
    return redirect('marketplace')


@login_required(login_url='login')
def checkout(request):
    if not _patient_only(request):
        return redirect('doctor_dashboard')

    cart = _cart_context(request.user)
    if not cart['cart_items']:
        messages.info(request, 'Add an item to your basket before checking out.')
        return redirect('marketplace')

    if request.method == 'POST':
        required = ('full_name', 'address', 'city', 'postal_code', 'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature')
        if any(not request.POST.get(field, '').strip() for field in required):
            messages.error(request, 'Complete the delivery details and payment to continue.')
        elif not _razorpay_test_configured():
            messages.error(request, 'Payment is not configured yet.')
        elif any(item.quantity > item.product.stock for item in cart['cart_items']):
            messages.error(request, 'One or more items no longer have enough stock. Please review your basket.')
        else:
            try:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                client.utility.verify_payment_signature({
                    'razorpay_payment_id': request.POST['razorpay_payment_id'],
                    'razorpay_order_id': request.POST['razorpay_order_id'],
                    'razorpay_signature': request.POST['razorpay_signature'],
                })
                order = client.order.fetch(request.POST['razorpay_order_id'])
                if (
                    order.get('currency') != 'INR'
                    or int(order.get('amount', 0)) != int(cart['cart_total'] * 100)
                ):
                    raise ValueError('Payment amount mismatch.')
            except (razorpay.errors.SignatureVerificationError, razorpay.errors.BadRequestError, ValueError):
                messages.error(request, 'The payment could not be verified. No order was placed.')
            else:
                order_reference = f"OASIS-{timezone.now():%m%d%H%M%S}"
                for item in cart['cart_items']:
                    item.product.stock -= item.quantity
                    item.product.save(update_fields=('stock', 'updated_at'))
                    item.delete()
                return render(request, 'patient_portal/checkout.html', {'order_placed': True, 'order_reference': order_reference})
        cart = _cart_context(request.user)

    return render(request, 'patient_portal/checkout.html', {**cart, 'razorpay_key_id': settings.RAZORPAY_KEY_ID})


@login_required(login_url='login')
@require_POST
def create_payment_order(request):
    if not _patient_only(request):
        return JsonResponse({'error': 'Marketplace is only available in the patient portal.'}, status=403)
    if not _razorpay_test_configured():
        return JsonResponse({'error': 'Razorpay test keys are not configured on the server.'}, status=503)
    cart = _cart_context(request.user)
    if not cart['cart_items']:
        return JsonResponse({'error': 'Your basket is empty.'}, status=400)
    if any(item.quantity > item.product.stock for item in cart['cart_items']):
        return JsonResponse({'error': 'One or more items no longer have enough stock.'}, status=409)
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            'amount': int(cart['cart_total'] * 100),
            'currency': 'INR',
            'receipt': f'oasis_{request.user.pk}_{timezone.now():%Y%m%d%H%M%S}',
            'notes': {'user_id': str(request.user.pk)},
        })
    except razorpay.errors.BadRequestError:
        return JsonResponse({'error': 'Razorpay could not create the payment order.'}, status=502)
    return JsonResponse({'key_id': settings.RAZORPAY_KEY_ID, 'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency']})
