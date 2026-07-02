from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Uživatel")
    
    name = models.CharField(max_length=50, blank=True, verbose_name="Jméno a příjmení")
    address = models.CharField(max_length=200, blank=True, verbose_name="Adresa")
    ico = models.CharField(max_length=20, blank=True, null=True, verbose_name="IČO")
    email = models.CharField(max_length=200, blank=True, null=True, verbose_name="E-mail")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    bank_account = models.CharField(max_length=50, blank=True, null=True, verbose_name="IBAN")
    bank_account_alt = models.CharField(max_length=50, blank=True, null=True, verbose_name="Číslo účtu")
    
    def __str__(self):
        return f"Profil: {self.user.username}"

class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Název / Jméno")
    address = models.CharField(max_length=200, blank=True, verbose_name="Adresa")
    ico = models.CharField(max_length=20, blank=True, null=True, verbose_name="IČO")
    email = models.CharField(max_length=200, blank=True, null=True, verbose_name="E-mail")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    notes = models.TextField(blank=True, verbose_name="Poznámka ke klientovi")

    def __str__(self):
        return self.name

class Gig(models.Model):
    STATUS_CHOICES = [
        ('planned', 'V plánu'),
        ('ongoing', 'Probíhá'),
        ('done', 'Hotovo'),
        ('paid', 'Zaplaceno'),
    ]

    name = models.CharField(max_length=200, verbose_name="Název akce")
    date = models.DateField(verbose_name="Datum konání")
    
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, verbose_name="Klient")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="Stav")
    
    notes = models.TextField(blank=True, verbose_name="Poznámky")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Autor")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.date} - {self.name}"

    def get_total_work_price(self):
        return sum(phase.get_price() for phase in self.work_phases.all())

    def get_total_equipment_price(self):
        return sum(eq.get_total_price() for eq in self.equipment_used.all())

    def get_total_custom_items_price(self):
        return sum(item.get_total_price() for item in self.custom_items.all())

    def get_total_price(self):
        return self.get_total_work_price() + self.get_total_equipment_price() + self.get_total_custom_items_price()


class WorkPhase(models.Model):
    """Zaznamenává odpracovaný čas na konkrétní akci."""
    
    class PhaseType(models.TextChoices):
        TRAVEL = 'TRV', _('Cesta (Travel)')
        SETUP = 'SET', _('Příprava (Setup)')
        SOUND = 'SND', _('Zvučení (Sound)')
        TEARDOWN = 'TDR', _('Bourání (Teardown)')

    # Zde jsme přidali definici tvých pevných sazeb
    class RateChoices(models.IntegerChoices):
        RATE_250 = 250, _('250 Kč/h')
        RATE_300 = 300, _('300 Kč/h')
        RATE_350 = 350, _('350 Kč/h')
        RATE_400 = 400, _('400 Kč/h')
        RATE_450 = 450, _('450 Kč/h')
        RATE_500 = 500, _('500 Kč/h')

    gig = models.ForeignKey('Gig', on_delete=models.CASCADE, related_name='work_phases')
    phase = models.CharField(max_length=3, choices=PhaseType.choices, default=PhaseType.SOUND, verbose_name="Fáze")
    
    start_time = models.DateTimeField(verbose_name="Čas OD")
    end_time = models.DateTimeField(verbose_name="Čas DO")
    
    # Zde jsme změnili pole na IntegerField (celá čísla stačí) a přidali volbu "choices"
    hourly_rate = models.IntegerField(
        choices=RateChoices.choices, 
        default=RateChoices.RATE_250, 
        verbose_name="Sazba (Kč/h)"
    )

    def get_duration_hours(self):
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600

    def get_price(self):
        from decimal import Decimal
        hours = Decimal(str(self.get_duration_hours()))
        return hours * Decimal(self.hourly_rate)


class Equipment(models.Model):
    name = models.CharField(max_length=150, verbose_name="Název vybavení (např. X32)")
    default_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Výchozí cena za akci")
    
    def __str__(self):
        return self.name


class GigEquipment(models.Model):
    """Mezivazební tabulka: jaká technika jela na jakou akci."""
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='equipment_used')
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Počet kusů")
    agreed_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Sjednaná cena za kus")

    def get_total_price(self):
        return self.quantity * self.agreed_price


class CustomInvoiceItem(models.Model):
    """Vlastní položka na faktuře - umožňuje přidat další díly, služby apod."""
    
    ITEM_TYPE_CHOICES = [
        ('fixed', 'Fixní cena'),
        ('hourly', 'Hodinová sazba'),
    ]

    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='custom_items')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES, default='fixed', verbose_name="Typ položky")
    description = models.CharField(max_length=250, verbose_name="Popis položky")
    
    # Pro fixní cenu
    fixed_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Fixní cena (Kč)")
    
    # Pro hodinovou sazbu
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1, null=True, blank=True, verbose_name="Počet hodin")
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Cena za hodinu (Kč/h)")

    class Meta:
        verbose_name = "Vlastní položka na faktuře"
        verbose_name_plural = "Vlastní položky na faktuře"
        ordering = ['id']

    def __str__(self):
        return f"{self.description} ({self.get_item_type_display()})"

    def get_total_price(self):
        if self.item_type == 'fixed':
            return self.fixed_price or 0
        else:  # hourly
            from decimal import Decimal
            qty = Decimal(str(self.quantity or 0))
            price = Decimal(str(self.unit_price or 0))
            return qty * price


class InvoiceSnapshot(models.Model):
    """Uložený stav faktury v konkrétním čase - immutable snapshot."""
    
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='invoice_snapshots', verbose_name="Akce")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Autor")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Uloženo")
    invoice_number = models.CharField(max_length=100, blank=True, verbose_name="Číslo faktury")
    
    # Snapshot dat
    work_phases_data = models.JSONField(default=list, verbose_name="Snapshot pracovních fází")
    equipment_data = models.JSONField(default=list, verbose_name="Snapshot techniky")
    custom_items_data = models.JSONField(default=list, verbose_name="Snapshot vlastních položek")
    
    # Celkové částky v čase uložení
    total_work_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cena za práci")
    total_equipment_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cena za techniku")
    total_custom_items_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Cena za ostatní")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Celková cena")
    
    class Meta:
        verbose_name = "Snapshot faktury"
        verbose_name_plural = "Snapshoty faktur"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice Snapshot - {self.gig.name} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"