from datetime import date
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Client, Gig, InvoiceSnapshot, UserProfile


class InvoicePaymentTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='invoice-user', password='test-pass')
		UserProfile.objects.create(user=self.user, bank_account='CZ123456789')
		self.client_record = Client.objects.create(name='Test klient')
		self.gig = Gig.objects.create(
			name='Test akce',
			date=date(2026, 10, 1),
			client=self.client_record,
			author=self.user,
		)
		self.client.force_login(self.user)

	def test_paid_invoice_records_date_and_suppresses_qr(self):
		response = self.client.post(
			reverse('save_invoice', args=[self.gig.id]),
			{'payment_method': 'cash', 'payment_date': '2026-10-05'},
		)

		self.assertRedirects(response, reverse('gig_detail', args=[self.gig.id]))
		snapshot = InvoiceSnapshot.objects.get(gig=self.gig)
		self.assertEqual(snapshot.payment_method, 'cash')
		self.assertEqual(snapshot.payment_date, date(2026, 10, 5))

		response = self.client.get(reverse('snapshot_pdf', args=[snapshot.id]))
		self.assertContains(response, 'Datum úhrady:')
		self.assertContains(response, 'Hotově')
		self.assertNotContains(response, 'QR Platba')

	def test_bank_transfer_does_not_require_or_store_due_date(self):
		response = self.client.post(
			reverse('save_invoice', args=[self.gig.id]),
			{'payment_method': 'bank_transfer', 'payment_date': '2026-10-05'},
		)

		self.assertRedirects(response, reverse('gig_detail', args=[self.gig.id]))
		snapshot = InvoiceSnapshot.objects.get(gig=self.gig)
		self.assertEqual(snapshot.payment_method, 'bank_transfer')
		self.assertIsNone(snapshot.due_date)

	def test_paid_invoice_requires_payment_date(self):
		response = self.client.post(
			reverse('save_invoice', args=[self.gig.id]),
			{'payment_method': 'bank_transfer'},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'U uhrazené faktury vyplňte datum úhrady.')
		self.assertFalse(InvoiceSnapshot.objects.filter(gig=self.gig).exists())

	def test_unpaid_invoice_keeps_due_date_and_qr(self):
		due_date = date(2026, 10, 25)
		self.client.post(
			reverse('save_invoice', args=[self.gig.id]),
			{'payment_method': 'unpaid', 'due_date': due_date.isoformat()},
		)
		snapshot = InvoiceSnapshot.objects.get(gig=self.gig)

		response = self.client.get(reverse('snapshot_pdf', args=[snapshot.id]))
		self.assertContains(response, 'Datum splatnosti:')
		self.assertContains(response, '25. 10. 2026')
		self.assertContains(response, snapshot.invoice_number)
		self.assertContains(response, 'QR Platba')

	def test_due_date_defaults_to_fourteen_days_and_invoice_number_is_unique(self):
		response = self.client.get(reverse('save_invoice', args=[self.gig.id]))
		expected_due_date = timezone.localdate() + timedelta(days=14)
		self.assertContains(response, f'value="{expected_due_date.isoformat()}"')

		post_data = {'payment_method': 'unpaid', 'due_date': expected_due_date.isoformat()}
		self.client.post(reverse('save_invoice', args=[self.gig.id]), post_data)
		first_snapshot = InvoiceSnapshot.objects.get(gig=self.gig)
		self.client.post(reverse('save_invoice', args=[self.gig.id]), post_data)
		second_snapshot = InvoiceSnapshot.objects.order_by('-id').first()

		self.assertNotEqual(first_snapshot.invoice_number, second_snapshot.invoice_number)
		self.assertRegex(first_snapshot.invoice_number, r'^\d{4}-\d{5}$')


class WorkspaceViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Equipment, GigEquipment, WorkPhase, CustomInvoiceItem
        cls.user = User.objects.create_user(username='producer', password='test-pass')
        cls.other_user = User.objects.create_user(username='other-producer')
        cls.customer = Client.objects.create(name='Signal Studio')
        cls.gig = Gig.objects.create(
            author=cls.user, client=cls.customer, name='Live session',
            date=date(2026, 10, 20), status='planned',
        )
        cls.other_gig = Gig.objects.create(
            author=cls.other_user, name='Private session', date=date(2026, 10, 20),
        )
        cls.phase = WorkPhase.objects.create(
            gig=cls.gig, start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2), hourly_rate=300,
        )
        gear = Equipment.objects.create(name='Mixing console', default_price=1200)
        cls.equipment = GigEquipment.objects.create(
            gig=cls.gig, equipment=gear, quantity=1, agreed_price=1200,
        )
        cls.item = CustomInvoiceItem.objects.create(
            gig=cls.gig, description='Transport', item_type='hourly', quantity=2, unit_price=500,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_workspace_pages_render_with_populated_records(self):
        routes = [
            ('gig_list', []), ('financial_overview', []), ('gig_detail', [self.gig.pk]),
            ('gig_create', []), ('gig_update', [self.gig.pk]), ('client_create', []),
            ('workphase_create', [self.gig.pk]), ('workphase_update', [self.phase.pk]),
            ('gigequipment_create', [self.gig.pk]),
            ('custom_invoice_item_create', [self.gig.pk]),
            ('custom_invoice_item_update', [self.item.pk]), ('save_invoice', [self.gig.pk]),
            ('gig_delete', [self.gig.pk]), ('workphase_delete', [self.phase.pk]),
            ('gigequipment_delete', [self.equipment.pk]),
            ('custom_invoice_item_delete', [self.item.pk]), ('gig_print', [self.gig.pk]),
        ]
        for route, args in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'cdn.jsdelivr.net')

    def test_search_matches_event_or_client_and_keeps_records_private(self):
        for query in ['live', 'SIGNAL', 'session']:
            with self.subTest(query=query):
                response = self.client.get(reverse('gig_list'), {'q': query})
                self.assertEqual(list(response.context['gigs']), [self.gig])
                self.assertNotContains(response, 'Private session')
        response = self.client.get(reverse('gig_list'), {'q': 'missing'})
        self.assertEqual(list(response.context['gigs']), [])
        self.assertContains(response, 'Žádné odpovídající akce')

    def test_filters_apply_to_calendar_and_list_and_survive_month_navigation(self):
        response = self.client.get(reverse('gig_list'), {
            'q': 'Signal', 'status': 'planned', 'client': self.customer.pk,
            'date_from': '2026-10-01', 'date_to': '2026-10-31',
            'month': 10, 'year': 2026, 'view': 'list',
        })
        self.assertEqual(list(response.context['gigs']), [self.gig])
        calendar_gigs = [gig for week in response.context['calendar_data']['weeks'] for day in week for gig in day['gigs']]
        self.assertEqual(calendar_gigs, [self.gig])
        first_day = next(day for week in response.context['calendar_data']['weeks'] for day in week if day['day'])
        self.assertEqual(first_day['weekday'], 'Čtvrtek')
        from html import unescape
        from html.parser import HTMLParser
        from urllib.parse import parse_qs, urlparse
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'a' and values.get('aria-label') == 'Další měsíc':
                    self.urls.append(values['href'])
        parser = Links()
        parser.feed(response.content.decode())
        params = parse_qs(urlparse(unescape(parser.urls[0])).query)
        self.assertEqual(params['month'], ['11'])
        self.assertEqual(params['q'], ['Signal'])
        self.assertEqual(params['view'], ['list'])
        self.assertEqual(params['status'], ['planned'])
        self.assertEqual(params['date_to'], ['2026-10-31'])

    def test_invalid_calendar_parameters_fall_back_to_current_month(self):
        for month, year in [('0', '2026'), ('13', '2026'), ('2', '0'), ('2', '10000'), ('oops', '2026')]:
            with self.subTest(month=month, year=year):
                response = self.client.get(reverse('gig_list'), {'month': month, 'year': year})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['calendar_data']['month'], date.today().month)

    def test_empty_workspace_and_login_error_render(self):
        self.client.force_login(self.other_user)
        Gig.objects.filter(author=self.other_user).delete()
        response = self.client.get(reverse('gig_list'))
        self.assertContains(response, 'Tvoje další akce začíná tady')
        self.assertContains(response, 'Prostor pro další akci')
        self.client.logout()
        response = self.client.post(reverse('login'), {'username': 'producer', 'password': 'wrong'})
        self.assertContains(response, 'Zkontroluj uživatelské jméno a heslo')

    def test_invalid_hourly_item_keeps_bound_selection_and_errors(self):
        response = self.client.post(reverse('custom_invoice_item_create', args=[self.gig.pk]), {
            'item_type': 'hourly', 'description': '', 'quantity': '2', 'unit_price': '500',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form']['item_type'].value(), 'hourly')
        self.assertTrue(response.context['form']['description'].errors)
        self.assertInHTML(
            '<input type="radio" name="item_type" value="hourly" class="field-radio" required id="id_item_type_1" checked>',
            response.content.decode(),
        )
