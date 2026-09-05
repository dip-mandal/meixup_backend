import hashlib
import hmac
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from common.config import settings

router = APIRouter(prefix="/payments", tags=["Payments"])


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., ge=100, description="Amount in paise; minimum 100 paise")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    receipt: str | None = Field(default=None, max_length=40)


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


@router.post("/create-order")
async def create_order(payload: CreateOrderRequest):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")

    receipt = payload.receipt or f"rcpt_{uuid.uuid4().hex[:24]}"
    request_body = {
        "amount": payload.amount,
        "currency": payload.currency.upper(),
        "receipt": receipt,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/orders",
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                json=request_body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach Razorpay") from exc

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Razorpay authentication failed")
    if response.is_error:
        raise HTTPException(status_code=500, detail="Razorpay order creation failed")

    order = response.json()
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
    }


@router.post("/verify-payment")
async def verify_payment(payload: VerifyPaymentRequest):
    message = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}"
    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    return {
        "success": True,
        "razorpay_payment_id": payload.razorpay_payment_id,
        "razorpay_order_id": payload.razorpay_order_id,
    }
