from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_invoicesnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicesnapshot',
            name='payment_method',
            field=models.CharField(
                choices=[('unpaid', 'Nezaplaceno'), ('cash', 'Hotově'), ('bank_transfer', 'Bankovním převodem')],
                default='unpaid',
                max_length=20,
                verbose_name='Způsob úhrady',
            ),
        ),
        migrations.AddField(
            model_name='invoicesnapshot',
            name='payment_date',
            field=models.DateField(blank=True, null=True, verbose_name='Datum úhrady'),
        ),
    ]