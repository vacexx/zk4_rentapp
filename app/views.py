from django.shortcuts import render, get_object_or_404, redirect
from .models import Gig
from .forms import GigForm, WorkPhaseForm, WorkPhase, GigEquipmentForm, GigEquipment, ClientForm, Client
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import urllib.parse

@login_required
def gig_detail(request, gig_id):
    gig = get_object_or_404(Gig, id=gig_id)
    
    context = {
        'gig': gig,
        'phases': gig.work_phases.all(),
        'equipment': gig.equipment_used.all(),
    }
    return render(request, 'gigs/gig_detail.html', context)

@login_required
def gig_list(request):
    """Výpis akcí s možností filtrování podle statusu a autora."""
    gigs = Gig.objects.all().order_by('-date')

    status_filter = request.GET.get('status')
    author_filter = request.GET.get('author')

    if status_filter:
        gigs = gigs.filter(status=status_filter)
    
    if author_filter:
        gigs = gigs.filter(author__id=author_filter)

    context = {
        'gigs': gigs,
        'users': User.objects.all(),
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
            gig = form.save(commit=False)
            if request.user.is_authenticated:
                gig.author = request.user 
            gig.save()                  
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
            phase = form.save(commit=False)
            phase.gig = gig
            phase.save()
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = WorkPhaseForm()
    return render(request, 'gigs/workphase_form.html', {'form': form, 'gig': gig})

@login_required
def workphase_update(request, phase_id):
    """Úprava existující fáze."""
    phase = get_object_or_404(WorkPhase, id=phase_id)
    if request.method == 'POST':
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
            eq = form.save(commit=False)
            eq.agreed_price = eq.equipment.default_price 
            eq.save()   
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
    gig = get_object_or_404(Gig, id=gig_id)
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

    qr_url = None
    if gig.author and hasattr(gig.author, 'profile') and gig.author.profile.bank_account:
        iban = gig.author.profile.bank_account.replace(" ", "")
        amount = f"{gig.get_total_price():.2f}"
        vs = f"{gig.date.strftime('%Y%m%d')}{gig.id}"
        spd_string = f"SPD*1.0*ACC:{iban}*AM:{amount}*CC:CZK*X-VS:{vs}"
        safe_spd = urllib.parse.quote(spd_string)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={safe_spd}"

    context = {
        'gig': gig,
        'phases': phases,
        'equipment': equipment,
        'qr_url': qr_url,
    }
    
    return render(request, 'gigs/gig_print.html', context)

@login_required
def client_create(request):
    """Jednoduché přidání nového klienta."""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gig_create') 
    else:
        form = ClientForm()
    
    return render(request, 'gigs/client_create.html', {'form': form})

@login_required
def gig_update(request, gig_id):
    """Úprava existující akce (změna stavu, data, klienta...)."""
    gig = get_object_or_404(Gig, id=gig_id)
    
    if request.method == 'POST':
        form = GigForm(request.POST, instance=gig)
        if form.is_valid():
            form.save()
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = GigForm(instance=gig)

    return render(request, 'gigs/gig_form.html', {'form': form, 'gig': gig, 'is_update': True})