from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_marketplace_products(apps, schema_editor):
    Product = apps.get_model('accounts', 'MarketplaceProduct')
    products = [
        ('Screen Comfort Lens Wipes', 'screen-comfort-lens-wipes', 'screen_comfort', 'Pre-moistened wipes for smudge-free lenses and screens.', 'A soft, individually wrapped lens wipe for glasses, sunglasses, and device screens. Use only on a cool, dry surface.', 'images/marketplace/lens-wipes.svg', Decimal('249.00'), 48, 'Screen-day essential', True),
        ('Preservative-Free Lubricating Drops', 'lubricating-drops', 'dry_eye', 'Single-use lubricating drops for occasional dryness.', 'Preservative-free artificial tears in convenient single-use vials. Follow the package directions and speak with an eye-care professional for persistent symptoms.', 'images/marketplace/lubricating-drops.svg', Decimal('425.00'), 36, 'Dryness support', True),
        ('Warm Eye Compress', 'warm-eye-compress', 'dry_eye', 'Reusable warm compress for a calming eye-care routine.', 'A microwave-free reusable compress designed for a comfortable warm routine. Do not use if it feels too hot and stop if discomfort occurs.', 'images/marketplace/warm-compress.svg', Decimal('699.00'), 22, 'At-home routine', True),
        ('UV400 Everyday Sunglasses', 'uv400-everyday-sunglasses', 'protection', 'Polarised everyday eyewear with UV400-labelled lenses.', 'Lightweight protective sunglasses for outdoor comfort. They are not a substitute for prescription safety eyewear or clinical treatment.', 'images/marketplace/sunglasses.svg', Decimal('1299.00'), 18, 'Outdoor care', False),
        ('Contact Lens Travel Kit', 'contact-lens-travel-kit', 'lens_care', 'Compact case, refillable bottle, and clean-hands reminder card.', 'A tidy travel set for lens-care essentials. Replace lens cases regularly and use only the lens solution recommended by your eye-care professional.', 'images/marketplace/lens-kit.svg', Decimal('549.00'), 30, 'Lens care', False),
        ('20-20-20 Desk Timer', '20-20-20-desk-timer', 'everyday', 'A quiet visual reminder to take regular screen breaks.', 'A simple desk timer that helps you follow a screen-break habit. It supports comfort routines and does not assess or treat vision conditions.', 'images/marketplace/desk-timer.svg', Decimal('799.00'), 14, 'Screen break helper', False),
    ]
    for name, slug, category, short_description, details, image_path, price, stock, badge, featured in products:
        Product.objects.update_or_create(
            slug=slug,
            defaults={
                'name': name, 'category': category, 'short_description': short_description,
                'details': details, 'image_path': image_path, 'price': price, 'stock': stock,
                'badge': badge, 'is_featured': featured, 'is_active': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('accounts', '0008_colourvisionsession')]

    operations = [
        migrations.CreateModel(
            name='MarketplaceProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=140)),
                ('slug', models.SlugField(unique=True)),
                ('category', models.CharField(choices=[('screen_comfort', 'Screen comfort'), ('dry_eye', 'Dry-eye support'), ('lens_care', 'Lens care'), ('protection', 'Eye protection'), ('everyday', 'Everyday care')], max_length=32)),
                ('short_description', models.CharField(max_length=220)),
                ('details', models.TextField(max_length=1200)),
                ('image_path', models.CharField(help_text='Path relative to the static directory.', max_length=220)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('stock', models.PositiveIntegerField(default=0)),
                ('badge', models.CharField(blank=True, max_length=48)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ('-is_featured', 'category', 'name')},
        ),
        migrations.CreateModel(
            name='MarketplaceCartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveSmallIntegerField(default=1)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_items', to='accounts.marketplaceproduct')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_cart_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-updated_at',)},
        ),
        migrations.AddConstraint(model_name='marketplacecartitem', constraint=models.UniqueConstraint(fields=('user', 'product'), name='unique_marketplace_cart_item')),
        migrations.RunPython(seed_marketplace_products, migrations.RunPython.noop),
    ]
