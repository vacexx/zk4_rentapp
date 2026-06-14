from django.shortcuts import render, get_object_or_404, redirect
from .models import Gig, CustomInvoiceItem
from .forms import GigForm, WorkPhaseForm, WorkPhase, GigEquipmentForm, GigEquipment, ClientForm, Client, CustomInvoiceItemForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import urllib.parse
from datetime import datetime, timedelta
from django.db.models import Sum, Q
from decimal import Decimal

@login_required
def gig_detail(request, gig_id):
    gig = get_object_or_404(Gig, id=gig_id)
    
    context = {
        'gig': gig,
        'phases': gig.work_phases.all(),
        'equipment': gig.equipment_used.all(),
        'custom_items': gig.custom_items.all(),
    }
    return render(request, 'gigs/gig_detail.html', context)

@login_required
def gig_list(request):
    """Výpis akcí - jen ty, které vytvořil přihlášený uživatel."""
    gigs = Gig.objects.filter(author=request.user).order_by('-date')

    status_filter = request.GET.get('status')

    if status_filter:
        gigs = gigs.filter(status=status_filter)

    context = {
        'gigs': gigs,
        'current_status': status_filter,
    }
    return render(request, 'gigs/gig_list.html', context)

@login_required
def financial_overview(request):
    """Finanční přehled akcí - měsíční a roční souhrny, fakturováno/nefakturováno."""
    user_gigs = Gig.objects.filter(author=request.user)
    
    # Česká jména měsíců
    czech_months = {
        1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
        5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
        9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec'
    }
    
    # Agregace dat
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Celkový přehled
    total_price = Decimal('0')
    invoiced_price = Decimal('0')
    not_invoiced_price = Decimal('0')
    
    for gig in user_gigs:
        total = gig.get_total_price()
        if gig.status == 'paid':
            invoiced_price += total
        else:
            not_invoiced_price += total
    
    total_price = invoiced_price + not_invoiced_price
    
    # Výpočet procenta zaplacení
    invoiced_percentage = 0
    if total_price > 0:
        invoiced_percentage = (invoiced_price / total_price) * 100
    
    # Měsíční přehled (posledních 12 měsíců)
    monthly_data = []
    for i in range(11, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_year = month_date.year
        month_num = month_date.month
        
        month_gigs = user_gigs.filter(
            date__year=month_year,
            date__month=month_num
        )
        
        month_total = Decimal('0')
        month_invoiced = Decimal('0')
        month_not_invoiced = Decimal('0')
        
        for gig in month_gigs:
            total = gig.get_total_price()
            month_total += total
            if gig.status == 'paid':
                month_invoiced += total
            else:
                month_not_invoiced += total
        
        if month_gigs.exists():
            month_name = f"{czech_months[month_num]} {month_year}"
            month_name_short = month_date.strftime('%m/%Y')
            monthly_data.append({
                'month': month_name,
                'month_short': month_name_short,
                'total': month_total,
                'invoiced': month_invoiced,
                'not_invoiced': month_not_invoiced,
                'count': month_gigs.count(),
            })
    
    # Roční přehled
    yearly_data = {}
    for gig in user_gigs:
        year = gig.date.year
        if year not in yearly_data:
            yearly_data[year] = {
                'total': Decimal('0'),
                'invoiced': Decimal('0'),
                'not_invoiced': Decimal('0'),
                'count': 0,
            }
        
        total = gig.get_total_price()
        yearly_data[year]['total'] += total
        yearly_data[year]['count'] += 1
        
        if gig.status == 'paid':
            yearly_data[year]['invoiced'] += total
        else:
            yearly_data[year]['not_invoiced'] += total
    
    yearly_list = [
        {
            'year': year,
            'total': data['total'],
            'invoiced': data['invoiced'],
            'not_invoiced': data['not_invoiced'],
            'count': data['count'],
        }
        for year, data in sorted(yearly_data.items(), reverse=True)
    ]
    
    # Statistiky podle statusu
    status_stats = {}
    for status_choice, status_label in Gig.STATUS_CHOICES:
        status_gigs = user_gigs.filter(status=status_choice)
        status_total = Decimal('0')
        for gig in status_gigs:
            status_total += gig.get_total_price()
        
        status_stats[status_label] = {
            'count': status_gigs.count(),
            'total': status_total,
        }
    
    context = {
        'total_price': total_price,
        'invoiced_price': invoiced_price,
        'not_invoiced_price': not_invoiced_price,
        'invoiced_percentage': invoiced_percentage,
        'gig_count': user_gigs.count(),
        'monthly_data': monthly_data,
        'yearly_data': yearly_list,
        'status_stats': status_stats,
        'current_month': current_month,
        'current_year': current_year,
    }
    
    return render(request, 'gigs/financial_overview.html', context)

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
            eq.gig = gig
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
    custom_items = CustomInvoiceItem.objects.filter(gig=gig)

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
        'custom_items': custom_items,
        'qr_url': qr_url,
    }
    
    return render(request, 'gigs/gig_print.html', context)

@login_required
def gig_print(request, gig_id):
    gig = get_object_or_404(Gig, id=gig_id)
    
    phases = WorkPhase.objects.filter(gig=gig).order_by('start_time')
    equipment = GigEquipment.objects.filter(gig=gig)
    custom_items = CustomInvoiceItem.objects.filter(gig=gig)

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
        'custom_items': custom_items,
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

@login_required
def custom_invoice_item_create(request, gig_id):
    """Přidání vlastní položky na fakturu."""
    gig = get_object_or_404(Gig, id=gig_id)
    if request.method == 'POST':
        form = CustomInvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.gig = gig
            item.save()
            return redirect('gig_detail', gig_id=gig.id)
    else:
        form = CustomInvoiceItemForm()
    return render(request, 'gigs/custominvoiceitem_form.html', {'form': form, 'gig': gig})

@login_required
def custom_invoice_item_update(request, item_id):
    """Úprava vlastní položky na faktuře."""
    item = get_object_or_404(CustomInvoiceItem, id=item_id)
    if request.method == 'POST':
        form = CustomInvoiceItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('gig_detail', gig_id=item.gig.id)
    else:
        form = CustomInvoiceItemForm(instance=item)
    return render(request, 'gigs/custominvoiceitem_form.html', {'form': form, 'gig': item.gig, 'item': item, 'is_update': True})

@login_required
def custom_invoice_item_delete(request, item_id):
    """Smazání vlastní položky z faktury."""
    item = get_object_or_404(CustomInvoiceItem, id=item_id)
    gig_id = item.gig.id
    if request.method == 'POST':
        item.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/custominvoiceitem_confirm_delete.html', {'item': item})