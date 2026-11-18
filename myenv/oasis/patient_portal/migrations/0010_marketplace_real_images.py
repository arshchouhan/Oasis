from django.db import migrations


def use_real_product_images(apps, schema_editor):
    Product = apps.get_model('accounts', 'MarketplaceProduct')
    images = {
        'screen-comfort-lens-wipes': 'https://images.unsplash.com/photo-1574258495973-f010dfbb5371?auto=format&fit=crop&w=900&q=85',
        'lubricating-drops': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=900&q=85',
        'warm-eye-compress': 'https://images.unsplash.com/photo-1600334089648-b0d9d3028eb2?auto=format&fit=crop&w=900&q=85',
        'uv400-everyday-sunglasses': 'https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=900&q=85',
        'contact-lens-travel-kit': 'https://images.unsplash.com/photo-1583947215259-38e31be8751f?auto=format&fit=crop&w=900&q=85',
        '20-20-20-desk-timer': 'https://images.unsplash.com/photo-1506784983877-45594efa4cbe?auto=format&fit=crop&w=900&q=85',
    }
    for slug, image_url in images.items():
        Product.objects.filter(slug=slug).update(image_path=image_url)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0009_marketplaceproduct_marketplacecartitem')]

    operations = [migrations.RunPython(use_real_product_images, migrations.RunPython.noop)]
