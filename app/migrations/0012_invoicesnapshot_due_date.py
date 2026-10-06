from django.db import migrations, models


def assign_existing_invoice_numbers(apps, schema_editor):
    invoice_snapshot = apps.get_model('app', 'InvoiceSnapshot')
    for snapshot in invoice_snapshot.objects.order_by('pk').iterator():
        if not snapshot.invoice_number:
            snapshot.invoice_number = f'{snapshot.created_at.year}-{snapshot.pk:05d}'
            snapshot.save(update_fields=['invoice_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_invoice_snapshot_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicesnapshot',
            name='due_date',
            field=models.DateField(blank=True, null=True, verbose_name='Datum splatnosti'),
        ),
        migrations.RunPython(assign_existing_invoice_numbers, migrations.RunPython.noop),
    ]