from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Název / Jméno")
    ico = models.CharField(max_length=20, blank=True, null=True, verbose_name="IČO")
    email = models.CharField(max_length=200, blank=True, null=True, verbose_name="E-mail")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    notes = models.TextField(blank=True, verbose_name="Poznámka ke klientovi")

    def __str__(self):
        return self.name

class Gig(models.Model):
# MOŽNOSTI PRO STATUS
    STATUS_CHOICES = [
        ('planned', 'V plánu'),
        ('ongoing', 'Probíhá'),
        ('done', 'Hotovo'),
    ]

    name = models.CharField(max_length=200, verbose_name="Název akce")
    date = models.DateField(verbose_name="Datum konání")
    
    # NOVÉ VAZBY MÍSTO client_name
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, verbose_name="Klient")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="Stav")
    
    notes = models.TextField(blank=True, verbose_name="Poznámky")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Autor")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.date} - {self.name}"

    def get_total_work_price(self):
        """Sečte peníze za všechny odpracované fáze."""
        return sum(phase.get_price() for phase in self.work_phases.all())

    def get_total_equipment_price(self):
        """Sečte peníze za veškerou pronajatou techniku."""
        return sum(eq.get_total_price() for eq in self.equipment_used.all())

    def get_total_price(self):
        """Finální částka pro fakturu (Práce + Technika)."""
        return self.get_total_work_price() + self.get_total_equipment_price()


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
        """Spočítá délku trvání v hodinách."""
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600

    def get_price(self):
        """Vynásobí hodiny sazbou."""
        from decimal import Decimal
        hours = Decimal(str(self.get_duration_hours()))
        return hours * Decimal(self.hourly_rate)


class Equipment(models.Model):
    """Tvůj inventář - katalog věcí, které můžeš pronajímat."""
    name = models.CharField(max_length=150, verbose_name="Název vybavení (např. X32)")
    default_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Výchozí cena za akci")
    
    def __str__(self):
        return self.name


class GigEquipment(models.Model):
    """Spojovací tabulka: jaká technika jela na jakou akci."""
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='equipment_used')
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    
    quantity = models.PositiveIntegerField(default=1, verbose_name="Počet kusů")
    
    # Cenu kopírujeme z default_price při vytvoření, ale necháváme ji editovatelnou.
    # Někdy dáš klientovi slevu, jindy zdražíš, tak ať ti to nerozhodí minulé faktury.
    agreed_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Sjednaná cena za kus")

    def get_total_price(self):
        return self.quantity * self.agreed_price