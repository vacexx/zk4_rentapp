from django.shortcuts import render, get_object_or_404, redirect
from .models import Gig
from .forms import GigForm, WorkPhaseForm, WorkPhase, GigEquipmentForm, GigEquipment
from django.contrib.auth.decorators import login_required

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
    """Výpis všech akcí seřazených od nejnovější."""
    gigs = Gig.objects.all().order_by('-date')
    return render(request, 'gigs/gig_list.html', {'gigs': gigs})

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