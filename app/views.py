from django.shortcuts import render, get_object_or_404, redirect
from .models import Gig
from .forms import GigForm, WorkPhaseForm, WorkPhase, GigEquipmentForm, GigEquipment
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import urllib.parse

@login_required
def gig_detail(request, gig_id):
    # Najde akci podle ID, nebo vyhodí chybu 404, pokud neexistuje
    gig = get_object_or_404(Gig, id=gig_id)
    
    # Připravíme si data pro šablonu
    context = {
        'gig': gig,
        'phases': gig.work_phases.all(),
        'equipment': gig.equipment_used.all(),
    }
    return render(request, 'gigs/gig_detail.html', context)

@login_required
def gig_list(request):
    """Výpis akcí s možností filtrování podle statusu a autora."""
    # Začneme se všemi akcemi (případně tu nech .filter(author=request.user), 
    # pokud nechceš, aby tví kolegové viděli tvoje akce a naopak)
    gigs = Gig.objects.all().order_by('-date')

    # Přečteme si filtry z URL
    status_filter = request.GET.get('status')
    author_filter = request.GET.get('author')

    # Aplikujeme filtry, pokud byly zadány
    if status_filter:
        gigs = gigs.filter(status=status_filter)
    
    if author_filter:
        gigs = gigs.filter(author__id=author_filter)

    context = {
        'gigs': gigs,
        'users': User.objects.all(), # Potřebujeme pro výběr autora ve filtru
        'current_status': status_filter,
        'current_author': author_filter,
    }
    return render(request, 'gigs/gig_list.html', context)

@login_required
def gig_create(request):
    """Formulář pro novou akci."""
    if request.method == 'POST':
        form = GigForm(request.POST)
        if form.is_valid():
            gig = form.save(commit=False) # Zastavíme ukládání
            if request.user.is_authenticated:
                gig.author = request.user # Přiřadíme přihlášeného uživatele jako autora
            gig.save()                    # Nyní uložíme
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = GigForm()
    return render(request, 'gigs/gig_form.html', {'form': form})

@login_required
def gig_delete(request, gig_id):
    """Smazání celé akce."""
    gig = get_object_or_404(Gig, id=gig_id)
    if request.method == 'POST':
        gig.delete()
        return redirect('gig_list') # Po smazání se vrátíme na přehled všech akcí
    return render(request, 'gigs/gig_confirm_delete.html', {'gig': gig})

@login_required
def workphase_create(request, gig_id):
    """Přidání odpracovaného času (fáze) ke konkrétní akci."""
    gig = get_object_or_404(Gig, id=gig_id)
    if request.method == 'POST':
        form = WorkPhaseForm(request.POST)
        if form.is_valid():
            phase = form.save(commit=False) # Zatím neukládat do DB
            phase.gig = gig # Propojení s konkrétní akcí
            phase.save() # Teď uložit
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = WorkPhaseForm()
    return render(request, 'gigs/workphase_form.html', {'form': form, 'gig': gig})

@login_required
def workphase_update(request, phase_id):
    """Úprava existující fáze."""
    phase = get_object_or_404(WorkPhase, id=phase_id)
    if request.method == 'POST':
        # "instance=phase" říká Djangu, že neukládáme novou fázi, ale přepisujeme starou
        form = WorkPhaseForm(request.POST, instance=phase)
        if form.is_valid():
            form.save()
            return redirect('gig_detail', gig_id=phase.gig.id)
    else:
        form = WorkPhaseForm(instance=phase)
    return render(request, 'gigs/workphase_form.html', {'form': form, 'gig': phase.gig})

@login_required
def workphase_delete(request, phase_id):
    """Smazání fáze."""
    phase = get_object_or_404(WorkPhase, id=phase_id)
    gig_id = phase.gig.id
    if request.method == 'POST':
        phase.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/workphase_confirm_delete.html', {'phase': phase})

@login_required
def gigequipment_create(request, gig_id):
    """Přidání techniky k akci s automatickou cenou."""
    gig = get_object_or_404(Gig, id=gig_id)
    if request.method == 'POST':
        form = GigEquipmentForm(request.POST)
        if form.is_valid():
            eq = form.save(commit=False) # Zastavíme ukládání
            eq.gig = gig                 # Propojíme s akcí
            
            # MAGICKÝ ŘÁDEK ZDE:
            # Vezmeme výchozí cenu z katalogu a uložíme ji jako sjednanou cenu
            eq.agreed_price = eq.equipment.default_price 
            
            eq.save()                    # Nyní finálně uložíme do databáze
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = GigEquipmentForm()
    return render(request, 'gigs/gigequipment_form.html', {'form': form, 'gig': gig})

@login_required
def gigequipment_delete(request, eq_id):
    """Smazání techniky z akce."""
    equipment = get_object_or_404(GigEquipment, id=eq_id)
    gig_id = equipment.gig.id
    if request.method == 'POST':
        equipment.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/gigequipment_confirm_delete.html', {'equipment': equipment})

@login_required
def gig_print(request, gig_id):
    # 1. Najdeme konkrétní akci
    gig = get_object_or_404(Gig, id=gig_id)
    
    # 2. Vytáhneme fáze a techniku PŘÍMO propojenou s touto akcí
    # Tímto zajistíme, že tam nebude nic navíc
    phases = WorkPhase.objects.filter(gig=gig).order_by('start_time')
    equipment = GigEquipment.objects.filter(gig=gig)
    
    context = {
        'gig': gig,
        'phases': phases,
        'equipment': equipment,
    }
    
    return render(request, 'gigs/gig_print.html', context)

@login_required
def gig_print(request, gig_id):
    gig = get_object_or_404(Gig, id=gig_id)
    
    phases = WorkPhase.objects.filter(gig=gig).order_by('start_time')
    equipment = GigEquipment.objects.filter(gig=gig)
    
    # 1. PŘÍPRAVA QR PLATBY
    qr_url = None
    # Zkontrolujeme, jestli má autor vyplněný profil a v něm číslo účtu
    if gig.author and hasattr(gig.author, 'profile') and gig.author.profile.bank_account:
        # Bankovní aplikace vyžadují IBAN (ideálně bez mezer)
        iban = gig.author.profile.bank_account.replace(" ", "")
        
        # Částka musí mít přesně dvě desetinná místa (např. 1500.00)
        amount = f"{gig.get_total_price():.2f}"
        
        # Variabilní symbol, který jsme vymysleli (Datum + ID akce)
        vs = f"{gig.date.strftime('%Y%m%d')}{gig.id}"
        
        # Oficiální formát řetězce pro českou QR platbu
        spd_string = f"SPD*1.0*ACC:{iban}*AM:{amount}*CC:CZK*X-VS:{vs}"
        
        # Převedeme text tak, aby se dal bezpečně poslat v URL adrese
        safe_spd = urllib.parse.quote(spd_string)
        
        # Použijeme spolehlivou službu na vygenerování obrázku QR kódu
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={safe_spd}"

    context = {
        'gig': gig,
        'phases': phases,
        'equipment': equipment,
        'qr_url': qr_url, # Pošleme URL adresu obrázku do šablony
    }
    
    return render(request, 'gigs/gig_print.html', context)