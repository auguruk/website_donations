from odoo import http
from odoo.http import request
import stripe


class CustomStripeController(http.Controller):

    @http.route('/custom/subscription', type='http', auth='public', website=True)
    def subscription_form(self, **kwargs):
        return request.render('custom_stripe_subscription.subscription_form')

    @http.route('/custom/subscription/create', type='http', auth='public', csrf=False, methods=['POST'])
    def create_subscription(self, **post):

        amount = float(post.get("amount", 0))
        email = post.get("email")

        if amount <= 0 or not email:
            return "Invalid amount or email."

        # Stripe API key
        stripe.api_key = request.env["ir.config_parameter"].sudo().get_param("stripe.secret_key")

        product_id = request.env["ir.config_parameter"].sudo().get_param("stripe.product_id")
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")

        # Create recurring monthly Price in GBP
        price = stripe.Price.create(
            product=product_id,
            unit_amount=int(amount * 100),
            currency="gbp",
            recurring={"interval": "month"},
        )

        # Checkout session
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price.id, "quantity": 1}],
            success_url=f"{base_url}/payment/status?success=1",
            cancel_url=f"{base_url}/payment/status?canceled=1",
        )

        return request.redirect(session.url)
