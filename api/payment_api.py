"""
Payment API Integration for AI Fitness Coach

FastAPI routes for:
- Plugin purchases
- Subscription management
- Payment webhooks
- Transaction history
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Header
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import json
import logging
from datetime import datetime

# Import payment processor
from .payment_processor import PaymentProcessor, PaymentTransaction, SubscriptionPlan, create_payment_processor

# Pydantic models
class PluginPurchaseRequest(BaseModel):
    """Plugin purchase request"""
    plugin_id: str
    payment_method_id: Optional[str] = None

class SubscriptionRequest(BaseModel):
    """Subscription request"""
    plan_id: str
    payment_method_id: Optional[str] = None

class PaymentConfirmationRequest(BaseModel):
    """Payment confirmation request"""
    transaction_id: str
    payment_method_id: Optional[str] = None

class RefundRequest(BaseModel):
    """Refund request"""
    transaction_id: str
    amount: Optional[float] = None
    reason: Optional[str] = None

class SubscriptionCancellationRequest(BaseModel):
    """Subscription cancellation request"""
    subscription_id: str
    immediate: bool = False

class PaymentResponse(BaseModel):
    """Payment response"""
    success: bool
    transaction_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: str = "pending"
    message: str = ""

class SubscriptionResponse(BaseModel):
    """Subscription response"""
    success: bool
    subscription_id: Optional[str] = None
    client_secret: Optional[str] = None
    status: str = "pending"
    trial_end: Optional[int] = None
    message: str = ""

# Global payment processor
payment_processor: Optional[PaymentProcessor] = None

# API Router
router = APIRouter(prefix="/api/payments", tags=["Payments"])
subscription_router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

async def get_payment_processor() -> PaymentProcessor:
    """Dependency to get payment processor"""
    global payment_processor
    if payment_processor is None:
        payment_processor = create_payment_processor()
        await payment_processor.initialize()
    return payment_processor

# Payment endpoints
@router.post("/plugin/purchase/{user_id}", response_model=PaymentResponse)
async def purchase_plugin(
    user_id: str,
    purchase_request: PluginPurchaseRequest,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Purchase a plugin"""
    try:
        # Get plugin price (in real implementation, fetch from plugin manifest)
        plugin_prices = {
            "golf_pro": 15.99,
            "tennis_pro": 12.99,
            "basketball_skills": 14.99
        }
        
        amount = plugin_prices.get(purchase_request.plugin_id)
        if amount is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        
        # Create payment transaction
        transaction = await processor.create_plugin_payment(
            user_id=user_id,
            plugin_id=purchase_request.plugin_id,
            amount=amount
        )
        
        if not transaction:
            raise HTTPException(status_code=500, detail="Failed to create payment")
        
        # If payment method provided, confirm immediately
        if purchase_request.payment_method_id:
            success = await processor.confirm_payment(
                transaction.transaction_id,
                purchase_request.payment_method_id
            )
            
            status = "completed" if success else "failed"
        else:
            status = "requires_payment_method"
        
        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            client_secret=transaction.stripe_payment_intent_id,
            status=status,
            message=f"Plugin purchase {'completed' if status == 'completed' else 'initiated'}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Plugin purchase failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm", response_model=PaymentResponse)
async def confirm_payment(
    confirmation_request: PaymentConfirmationRequest,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Confirm a payment"""
    try:
        success = await processor.confirm_payment(
            confirmation_request.transaction_id,
            confirmation_request.payment_method_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Payment confirmation failed")
        
        return PaymentResponse(
            success=True,
            transaction_id=confirmation_request.transaction_id,
            status="completed",
            message="Payment confirmed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Payment confirmation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refund", response_model=PaymentResponse)
async def process_refund(
    refund_request: RefundRequest,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Process a refund"""
    try:
        success = await processor.process_refund(
            refund_request.transaction_id,
            refund_request.amount,
            refund_request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Refund processing failed")
        
        return PaymentResponse(
            success=True,
            transaction_id=refund_request.transaction_id,
            status="refunded",
            message="Refund processed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Refund processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transaction/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get transaction details"""
    try:
        transaction = await processor.get_transaction(transaction_id)
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {
            "transaction_id": transaction.transaction_id,
            "user_id": transaction.user_id,
            "payment_type": transaction.payment_type.value,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "status": transaction.status.value,
            "plugin_id": transaction.plugin_id,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
            "metadata": transaction.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get transaction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_payment_history(
    user_id: str,
    limit: int = 50,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get payment history for user"""
    try:
        transactions = await processor.get_user_transactions(user_id)
        
        # Limit results
        limited_transactions = transactions[:limit]
        
        transaction_list = []
        for transaction in limited_transactions:
            transaction_list.append({
                "transaction_id": transaction.transaction_id,
                "payment_type": transaction.payment_type.value,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "status": transaction.status.value,
                "plugin_id": transaction.plugin_id,
                "created_at": transaction.created_at,
                "updated_at": transaction.updated_at
            })
        
        return {
            "user_id": user_id,
            "transactions": transaction_list,
            "total_transactions": len(transactions),
            "returned_transactions": len(limited_transactions)
        }
        
    except Exception as e:
        logging.error(f"Get payment history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Subscription endpoints
@subscription_router.get("/plans")
async def get_subscription_plans(
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get available subscription plans"""
    try:
        plans = []
        for plan in processor.subscription_plans.values():
            plans.append({
                "plan_id": plan.plan_id,
                "name": plan.name,
                "description": plan.description,
                "price": plan.price,
                "currency": plan.currency,
                "interval": plan.interval,
                "trial_period_days": plan.trial_period_days,
                "features": plan.features
            })
        
        return {
            "plans": plans,
            "total": len(plans)
        }
        
    except Exception as e:
        logging.error(f"Get subscription plans failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.post("/subscribe/{user_id}", response_model=SubscriptionResponse)
async def create_subscription(
    user_id: str,
    subscription_request: SubscriptionRequest,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Create a subscription"""
    try:
        result = await processor.create_subscription_payment(
            user_id=user_id,
            plan_id=subscription_request.plan_id
        )
        
        if not result:
            raise HTTPException(status_code=400, detail="Subscription creation failed")
        
        return SubscriptionResponse(
            success=True,
            subscription_id=result["subscription_id"],
            client_secret=result.get("client_secret"),
            status=result["status"],
            trial_end=result.get("trial_end"),
            message="Subscription created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Subscription creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.get("/current/{user_id}")
async def get_current_subscription(
    user_id: str,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get current subscription for user"""
    try:
        subscription = await processor.get_user_subscription(user_id)
        
        if not subscription:
            return {
                "user_id": user_id,
                "subscription": None,
                "message": "No active subscription found"
            }
        
        return {
            "user_id": user_id,
            "subscription": {
                "subscription_id": subscription.subscription_id,
                "plan_id": subscription.plan_id,
                "status": subscription.status.value,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
                "created_at": subscription.created_at
            }
        }
        
    except Exception as e:
        logging.error(f"Get current subscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@subscription_router.post("/cancel")
async def cancel_subscription(
    cancellation_request: SubscriptionCancellationRequest,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Cancel a subscription"""
    try:
        # Extract user_id from subscription (in real implementation, verify ownership)
        user_id = "extracted_from_subscription"  # Mock
        
        success = await processor.cancel_subscription(
            user_id=user_id,
            subscription_id=cancellation_request.subscription_id,
            immediate=cancellation_request.immediate
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Subscription cancellation failed")
        
        return {
            "success": True,
            "subscription_id": cancellation_request.subscription_id,
            "immediate": cancellation_request.immediate,
            "message": "Subscription cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Subscription cancellation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoint
@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing stripe signature")
        
        # Process webhook in background
        background_tasks.add_task(
            _process_webhook,
            processor,
            payload.decode(),
            stripe_signature
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

async def _process_webhook(processor: PaymentProcessor, payload: str, signature: str):
    """Process webhook in background"""
    try:
        success = await processor.handle_webhook(payload, signature)
        if success:
            logging.info("✅ Webhook processed successfully")
        else:
            logging.error("❌ Webhook processing failed")
    except Exception as e:
        logging.error(f"Background webhook processing failed: {e}")

# Payment method management
@router.get("/methods/{user_id}")
async def get_payment_methods(
    user_id: str,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get saved payment methods for user"""
    try:
        # In real implementation, fetch from Stripe
        # This is a mock response
        return {
            "user_id": user_id,
            "payment_methods": [
                {
                    "id": "pm_mock_card_123",
                    "type": "card",
                    "card": {
                        "brand": "visa",
                        "last4": "4242",
                        "exp_month": 12,
                        "exp_year": 2025
                    },
                    "created": "2024-01-01T00:00:00Z"
                }
            ],
            "total": 1
        }
        
    except Exception as e:
        logging.error(f"Get payment methods failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Billing portal
@subscription_router.get("/portal/{user_id}")
async def get_billing_portal(
    user_id: str,
    return_url: str = "https://yourapp.com/account",
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get billing portal URL for user"""
    try:
        # In real implementation, create Stripe billing portal session
        portal_url = f"https://billing.stripe.com/p/session/mock_{user_id}"
        
        return {
            "portal_url": portal_url,
            "return_url": return_url,
            "expires_at": (datetime.now().timestamp() + 3600)  # 1 hour
        }
        
    except Exception as e:
        logging.error(f"Get billing portal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoints
@router.get("/analytics/revenue")
async def get_revenue_analytics(
    days: int = 30,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Get revenue analytics (admin only)"""
    try:
        # Mock analytics data
        return {
            "period_days": days,
            "total_revenue": 1250.50,
            "total_transactions": 85,
            "successful_transactions": 82,
            "failed_transactions": 3,
            "refunded_amount": 50.00,
            "plugin_sales": {
                "golf_pro": 15,
                "tennis_pro": 12,
                "basketball_skills": 8
            },
            "subscription_revenue": 780.00,
            "plugin_revenue": 470.50
        }
        
    except Exception as e:
        logging.error(f"Get revenue analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@router.get("/health")
async def payment_health_check():
    """Payment system health check"""
    try:
        processor = await get_payment_processor()
        
        # Test basic functionality
        test_passed = True
        error_message = None
        
        try:
            # Test customer creation
            customer_id = await processor._get_or_create_customer("health_check_user")
            if not customer_id:
                test_passed = False
                error_message = "Customer creation test failed"
        except Exception as e:
            test_passed = False
            error_message = str(e)
        
        return {
            "status": "healthy" if test_passed else "unhealthy",
            "stripe_enabled": processor.stripe_enabled,
            "test_passed": test_passed,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Payment health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Include routers in main app
def include_payment_routes(app):
    """Include payment routes in FastAPI app"""
    app.include_router(router)
    app.include_router(subscription_router)