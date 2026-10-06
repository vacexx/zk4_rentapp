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
