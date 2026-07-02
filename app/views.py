from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.core.signing import Signer, BadSignature
from .models import Gig, CustomInvoiceItem, WorkPhase, GigEquipment, Client
from .forms import GigForm, WorkPhaseForm, GigEquipmentForm, ClientForm, CustomInvoiceItemForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import urllib.parse
import calendar
from datetime import datetime, timedelta, date
from django.db.models import Sum, Q
from decimal import Decimal


def _ics_escape(value):
    if not value:
        return ''
    escaped = str(value).replace('\\', '\\\\')
    escaped = escaped.replace('\r\n', '\n').replace('\r', '\n')
    escaped = escaped.replace('\n', '\\n')
    escaped = escaped.replace(';', '\\;')
    escaped = escaped.replace(',', '\\,')
    return escaped


def _calendar_token_for_user(user):
    signer = Signer(salt='calendar-subscription')
    return signer.sign(str(user.pk))


def _user_from_calendar_token(token):
    signer = Signer(salt='calendar-subscription')
    try:
        user_id = signer.unsign(token)
        return User.objects.get(pk=user_id)
    except (BadSignature, User.DoesNotExist, ValueError):
        return None


def _get_user_gig_or_404(request, gig_id):
    return get_object_or_404(Gig, id=gig_id, author=request.user)

@login_required
def gig_detail(request, gig_id):
    gig = _get_user_gig_or_404(request, gig_id)
    
    from .models import InvoiceSnapshot
    invoice_snapshots = InvoiceSnapshot.objects.filter(gig=gig).order_by('-created_at')
    
    context = {
        'gig': gig,
        'phases': gig.work_phases.all(),
        'equipment': gig.equipment_used.all(),
        'custom_items': gig.custom_items.all(),
        'invoice_snapshots': invoice_snapshots,
    }
    return render(request, 'gigs/gig_detail.html', context)

@login_required
def gig_calendar_export(request, gig_id):
    gig = _get_user_gig_or_404(request, gig_id)
    phases = gig.work_phases.order_by('start_time')
    if phases.exists():
        start = phases.first().start_time
        end = phases.last().end_time
        dtstart = start.strftime('%Y%m%dT%H%M%S')
        dtend = end.strftime('%Y%m%dT%H%M%S')
    else:
        dtstart = gig.date.strftime('%Y%m%d')
        dtend = (gig.date + timedelta(days=1)).strftime('%Y%m%d')

    location = gig.client.address if gig.client and gig.client.address else ''
    description_lines = [f"Klient: {gig.client.name}" if gig.client else 'Klient: N/A']
    if gig.notes:
        description_lines.append('')
        description_lines.append(gig.notes)
    description = '\n'.join(description_lines)

    ics_lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//ZK4 RentApp//Apple Calendar Export//CZ',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:gig-{gig.id}@zk4_rentapp',
        f'DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}',
        f'SUMMARY:{_ics_escape(gig.name)}',
        f'DESCRIPTION:{_ics_escape(description)}',
        f'LOCATION:{_ics_escape(location)}',
        f'DTSTART:{dtstart}',
        f'DTEND:{dtend}',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    content = '\r\n'.join(ics_lines) + '\r\n'
    response = HttpResponse(content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="gig-{gig.id}.ics"'
    return response

@login_required
def calendar_subscription(request, token):
    user = _user_from_calendar_token(token)
    if not user:
        raise Http404()

    gigs = Gig.objects.filter(author=user).order_by('date')
    ics_lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//ZK4 RentApp//Calendar Subscription//CZ',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:ZK4 Production ({user.username})',
        'X-WR-TIMEZONE:Europe/Prague',
        'REFRESH-INTERVAL:PT15M',
        'X-PUBLISH-TTL:PT15M',
    ]

    for gig in gigs:
        phases = gig.work_phases.order_by('start_time')
        if phases.exists():
            start = phases.first().start_time
            end = phases.last().end_time
            dtstart = start.strftime('%Y%m%dT%H%M%S')
            dtend = end.strftime('%Y%m%dT%H%M%S')
        else:
            dtstart = gig.date.strftime('%Y%m%d')
            dtend = (gig.date + timedelta(days=1)).strftime('%Y%m%d')

        location = gig.client.address if gig.client and gig.client.address else ''
        description_lines = [f"Klient: {gig.client.name}" if gig.client else 'Klient: N/A']
        if gig.status:
            description_lines.append(f"Stav: {gig.get_status_display()}")
        if gig.notes:
            description_lines.append('')
            description_lines.append(gig.notes)
        description = '\n'.join(description_lines)

        ics_lines.extend([
            'BEGIN:VEVENT',
            f'UID:calendar-{user.pk}-gig-{gig.id}@zk4_rentapp',
            f'DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}',
            f'SUMMARY:{_ics_escape(gig.name)}',
            f'DESCRIPTION:{_ics_escape(description)}',
            f'LOCATION:{_ics_escape(location)}',
            f'DTSTART:{dtstart}',
            f'DTEND:{dtend}',
            'END:VEVENT',
        ])

    ics_lines.append('END:VCALENDAR')
    content = '\r\n'.join(ics_lines) + '\r\n'
    response = HttpResponse(content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="zk4-production-gigs.ics"'
    # Cache-busting headers to ensure Apple Calendar always fetches the latest version
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
def gig_list(request):
    """Výpis akcí - jen ty, které vytvořil přihlášený uživatel."""
    gigs = Gig.objects.filter(author=request.user).order_by('-date')

    status_filter = request.GET.get('status')
    client_filter = request.GET.get('client')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if status_filter:
        gigs = gigs.filter(status=status_filter)

    if client_filter:
        try:
            gigs = gigs.filter(client_id=int(client_filter))
        except (ValueError, TypeError):
            client_filter = None

    if date_from:
        try:
            date_from_value = date.fromisoformat(date_from)
            gigs = gigs.filter(date__gte=date_from_value)
        except ValueError:
            date_from = None

    if date_to:
        try:
            date_to_value = date.fromisoformat(date_to)
            gigs = gigs.filter(date__lte=date_to_value)
        except ValueError:
            date_to = None

    clients = Client.objects.filter(gig__author=request.user).distinct().order_by('name')
    today = date.today()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year

    czech_months = {
        1: 'Leden', 2: 'Únor', 3: 'Březen', 4: 'Duben',
        5: 'Květen', 6: 'Červen', 7: 'Červenec', 8: 'Srpen',
        9: 'Září', 10: 'Říjen', 11: 'Listopad', 12: 'Prosinec'
    }

    month_gigs = gigs.filter(date__year=year, date__month=month)
    gigs_by_day = {}
    for gig in month_gigs:
        gigs_by_day.setdefault(gig.date.day, []).append(gig)

    cal = calendar.Calendar(firstweekday=0)
    month_weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_days = []
        for day in week:
            week_days.append({
                'day': day,
                'gigs': gigs_by_day.get(day, []) if day else [],
            })
        month_weeks.append(week_days)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    calendar_data = {
        'month_name': czech_months.get(month, calendar.month_name[month]),
        'month': month,
        'year': year,
        'weeks': month_weeks,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    }

    subscription_url = request.build_absolute_uri(
        reverse('calendar_subscription', args=[_calendar_token_for_user(request.user)])
    )

    context = {
        'gigs': gigs,
        'current_status': status_filter,
        'current_client': client_filter,
        'date_from': date_from,
        'date_to': date_to,
        'clients': clients,
        'today': today,
        'calendar_data': calendar_data,
        'subscription_url': subscription_url,
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
    gig = _get_user_gig_or_404(request, gig_id)
    if request.method == 'POST':
        gig.delete()
        return redirect('gig_list')
    return render(request, 'gigs/gig_confirm_delete.html', {'gig': gig})

@login_required
def workphase_create(request, gig_id):
    """Přidání odpracovaného času (fáze) ke konkrétní akci."""
    gig = _get_user_gig_or_404(request, gig_id)
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
    phase = get_object_or_404(WorkPhase, id=phase_id, gig__author=request.user)
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
    phase = get_object_or_404(WorkPhase, id=phase_id, gig__author=request.user)
    gig_id = phase.gig.id
    if request.method == 'POST':
        phase.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/workphase_confirm_delete.html', {'phase': phase})

@login_required
def gigequipment_create(request, gig_id):
    """Přidání techniky k akci s automatickou cenou."""
    gig = _get_user_gig_or_404(request, gig_id)
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
    equipment = get_object_or_404(GigEquipment, id=eq_id, gig__author=request.user)
    gig_id = equipment.gig.id
    if request.method == 'POST':
        equipment.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/gigequipment_confirm_delete.html', {'equipment': equipment})

@login_required
def gig_print(request, gig_id):
    gig = _get_user_gig_or_404(request, gig_id)
    
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
def snapshot_pdf(request, snapshot_id):
    """Display a saved invoice snapshot in print-friendly format."""
    from .models import InvoiceSnapshot
    
    snapshot = get_object_or_404(InvoiceSnapshot, id=snapshot_id, author=request.user)
    gig = snapshot.gig
    
    # Build QR code URL if bank account available
    qr_url = None
    if gig.author and hasattr(gig.author, 'profile') and gig.author.profile.bank_account:
        iban = gig.author.profile.bank_account.replace(" ", "")
        amount = f"{snapshot.total_price:.2f}"
        vs = f"{gig.date.strftime('%Y%m%d')}{gig.id}"
        spd_string = f"SPD*1.0*ACC:{iban}*AM:{amount}*CC:CZK*X-VS:{vs}"
        safe_spd = urllib.parse.quote(spd_string)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={safe_spd}"
    
    context = {
        'gig': gig,
        'snapshot': snapshot,
        'qr_url': qr_url,
        'is_snapshot': True,
    }
    
    return render(request, 'gigs/snapshot_print.html', context)

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
    gig = _get_user_gig_or_404(request, gig_id)
    
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
    gig = _get_user_gig_or_404(request, gig_id)
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
    item = get_object_or_404(CustomInvoiceItem, id=item_id, gig__author=request.user)
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
    item = get_object_or_404(CustomInvoiceItem, id=item_id, gig__author=request.user)
    gig_id = item.gig.id
    if request.method == 'POST':
        item.delete()
        return redirect('gig_detail', gig_id=gig_id)
    return render(request, 'gigs/custominvoiceitem_confirm_delete.html', {'item': item})


@login_required
def save_invoice(request, gig_id):
    """Uloží snapshot faktury v jejím aktuálním stavu."""
    from django.shortcuts import redirect
    from django.contrib import messages
    import json
    
    gig = get_object_or_404(Gig, id=gig_id, author=request.user)
    
    # Gather current invoice data
    work_phases = gig.work_phases.all()
    equipment = gig.equipment_used.all()
    custom_items = gig.custom_items.all()
    
    # Serialize work phases
    work_phases_data = []
    for phase in work_phases:
        work_phases_data.append({
            'id': phase.id,
            'phase': phase.get_phase_display(),
            'start_time': phase.start_time.isoformat(),
            'end_time': phase.end_time.isoformat(),
            'duration_hours': phase.get_duration_hours(),
            'hourly_rate': phase.hourly_rate,
            'price': float(phase.get_price()),
        })
    
    # Serialize equipment
    equipment_data = []
    for eq in equipment:
        equipment_data.append({
            'id': eq.id,
            'equipment_name': eq.equipment.name,
            'quantity': eq.quantity,
            'agreed_price': float(eq.agreed_price),
            'total_price': float(eq.get_total_price()),
        })
    
    # Serialize custom items
    custom_items_data = []
    for item in custom_items:
        custom_items_data.append({
            'id': item.id,
            'description': item.description,
            'item_type': item.item_type,
            'fixed_price': float(item.fixed_price or 0) if item.item_type == 'fixed' else None,
            'quantity': float(item.quantity or 0) if item.item_type == 'hourly' else None,
            'unit_price': float(item.unit_price or 0) if item.item_type == 'hourly' else None,
            'total_price': float(item.get_total_price()),
        })
    
    # Calculate totals
    total_work_price = gig.get_total_work_price()
    total_equipment_price = gig.get_total_equipment_price()
    total_custom_items_price = gig.get_total_custom_items_price()
    total_price = gig.get_total_price()
    
    # Create snapshot
    from .models import InvoiceSnapshot
    snapshot = InvoiceSnapshot.objects.create(
        gig=gig,
        author=request.user,
        work_phases_data=work_phases_data,
        equipment_data=equipment_data,
        custom_items_data=custom_items_data,
        total_work_price=total_work_price,
        total_equipment_price=total_equipment_price,
        total_custom_items_price=total_custom_items_price,
        total_price=total_price,
    )
    
    messages.success(request, f'Faktura byla úspěšně uložena ({snapshot.created_at.strftime("%d.%m.%Y %H:%M")})')
    return redirect('gig_detail', gig_id=gig_id)


@login_required
def delete_snapshot(request, snapshot_id):
    """Delete an invoice snapshot."""
    from django.contrib import messages
    from .models import InvoiceSnapshot
    
    snapshot = get_object_or_404(InvoiceSnapshot, id=snapshot_id, author=request.user)
    gig_id = snapshot.gig.id
    
    if request.method == 'POST':
        snapshot.delete()
        messages.success(request, 'Uložená faktura byla smazána.')
        return redirect('gig_detail', gig_id=gig_id)
    
    return render(request, 'gigs/snapshot_confirm_delete.html', {'snapshot': snapshot})
