from odoo import http
from odoo.http import request
import requests


class CustomStripeController(http.Controller):

    @http.route('/custom/subscription', type='http', auth='public', website=True)
    def subscription_form(self, **kwargs):
        return request.render('website_donations.subscription_form')

    @http.route('/custom/subscription/create', type='http', auth='public', csrf=False, methods=['POST'])
    def create_subscription(self, **post):

        amount = float(post.get("amount", 0))
        email = post.get("email")

        if amount <= 0 or not email:
            return "Invalid amount or email."

        # Get system parameters
        IrConfig = request.env["ir.config_parameter"].sudo()

        stripe = request.env['payment.provider'].search([
            ('code', '=', 'stripe'),
            ('state', '=', 'enabled'),
        ])

        secret_key = ''
        if stripe:
            secret_key = stripe.stripe_secret_key

        product_id = IrConfig.get_param("stripe.product_id")
        base_url = IrConfig.get_param("web.base.url")

        if not secret_key or not product_id:
            return "Stripe configuration missing!"

        # -----------------------------
        # 1. Create Stripe Price
        # -----------------------------
        price_resp = requests.post(
            "https://api.stripe.com/v1/prices",
            auth=(secret_key, ""),
            data={
                "product": product_id,
                "unit_amount": int(amount * 100),
                "currency": "gbp",
                "recurring[interval]": "month",
            },
            timeout=30
        )

        if price_resp.status_code >= 400:
            return "Stripe Price Error: %s" % price_resp.text

        price_id = price_resp.json().get("id")

        # -----------------------------
        # 2. Create Checkout Session
        # -----------------------------
        session_resp = requests.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(secret_key, ""),
            data={
                "mode": "subscription",
                "customer_email": email,
                "success_url": f"{base_url}/payment/status?success=1",
                "cancel_url": f"{base_url}/payment/status?canceled=1",

                # Line items must use this prefix format in REST
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
            },
            timeout=30
        )

        if session_resp.status_code >= 400:
            return "Stripe Session Error: %s" % session_resp.text

        session_url = session_resp.json().get("url")
        return request.redirect(session_url)