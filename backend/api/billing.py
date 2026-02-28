"""Stripe billing: checkout, portal, webhook, subscription status."""

import datetime as dt

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import User

router = APIRouter()


def _init_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/checkout-session")
def create_checkout_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe Checkout session for the subscription."""
    _init_stripe()
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        "success_url": f"{settings.FRONTEND_URL}/billing?success=1",
        "cancel_url": f"{settings.FRONTEND_URL}/billing?canceled=1",
        "metadata": {"user_id": str(user.id)},
        "allow_promotion_codes": True,
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    else:
        params["customer_email"] = user.email

    session = stripe.checkout.Session.create(**params)
    return {"url": session.url}


@router.post("/portal")
def create_portal_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Open Stripe Customer Portal to manage/cancel subscription."""
    if not user.stripe_customer_id:
        raise HTTPException(400, "No billing account found")
    _init_stripe()
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    return {"url": session.url}


@router.get("/status")
def billing_status(user: User = Depends(get_current_user)):
    """Return current subscription status."""
    return {
        "subscription_status": user.subscription_status,
        "subscription_ends_at": (
            user.subscription_ends_at.isoformat() if user.subscription_ends_at else None
        ),
        "has_active_subscription": user.subscription_status == "active",
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events. Signature-verified."""
    _init_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(400, "Invalid signature")

    _handle_event(event, db)
    return {"received": True}


def _handle_event(event: dict, db: Session):
    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = int(data["metadata"].get("user_id", 0))
        if not user_id:
            return
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.stripe_customer_id = data["customer"]
            user.stripe_subscription_id = data.get("subscription")
            user.subscription_status = "active"
            user.subscription_ends_at = None
            db.commit()

    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        _sync_subscription(data, db)

    elif etype == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.subscription_status = "past_due"
                db.commit()


def _sync_subscription(sub: dict, db: Session):
    customer_id = sub.get("customer")
    if not customer_id:
        return
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    status = sub.get("status", "")
    if status in ("active", "trialing"):
        user.subscription_status = "active"
        user.subscription_ends_at = None
    elif status == "canceled":
        user.subscription_status = "canceled"
        period_end = sub.get("current_period_end")
        if period_end:
            user.subscription_ends_at = dt.datetime.fromtimestamp(period_end, tz=dt.timezone.utc)
    elif status in ("past_due", "incomplete"):
        user.subscription_status = "past_due"
    else:
        user.subscription_status = "canceled"

    db.commit()
