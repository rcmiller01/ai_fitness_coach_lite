"""
Payment Processing System for AI Fitness Coach

Handles payment processing for:
- Plugin purchases
- Subscription management
- Trial activations
- Refunds and cancellations

Uses Stripe as the primary payment processor with webhook handling.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import hmac
import hashlib

# Payment processor dependencies
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logging.warning("Stripe library not available. Payment processing will be mocked.")

class PaymentStatus(Enum):
    """Payment status types"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentType(Enum):
    """Payment types"""
    PLUGIN_PURCHASE = "plugin_purchase"
    SUBSCRIPTION = "subscription"
    TRIAL_UPGRADE = "trial_upgrade"
    RENEWAL = "renewal"

class SubscriptionStatus(Enum):
    """Subscription status types"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    UNPAID = "unpaid"

@dataclass
class PaymentTransaction:
    """Payment transaction record"""
    transaction_id: str
    user_id: str
    payment_type: PaymentType
    amount: float
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING
    stripe_payment_intent_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    plugin_id: Optional[str] = None
    subscription_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SubscriptionPlan:
    """Subscription plan definition"""
    plan_id: str
    name: str
    description: str
    price: float
    currency: str = "USD"
    interval: str = "month"  # month, year
    trial_period_days: int = 0
    features: List[str] = None
    stripe_price_id: Optional[str] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = []

@dataclass
class CustomerSubscription:
    """Customer subscription record"""
    subscription_id: str
    user_id: str
    plan_id: str
    status: SubscriptionStatus
    current_period_start: str
    current_period_end: str
    stripe_subscription_id: Optional[str] = None
    trial_end: Optional[str] = None
    cancelled_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

class PaymentProcessor:
    """Main payment processing system"""
    
    def __init__(self, stripe_secret_key: str = None, webhook_secret: str = None, db_manager=None):
        self.db_manager = db_manager
        self.transactions = {}  # In-memory storage for mock mode
        self.subscriptions = {}
        self.customers = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize Stripe
        if STRIPE_AVAILABLE and stripe_secret_key:
            stripe.api_key = stripe_secret_key
            self.webhook_secret = webhook_secret
            self.stripe_enabled = True
            self.logger.info("✅ Stripe payment processor initialized")
        else:
            self.stripe_enabled = False
            self.logger.info("⚠️ Payment processor running in mock mode")
        
        # Default subscription plans
        self.subscription_plans = {
            "free": SubscriptionPlan(
                plan_id="free",
                name="Free Plan",
                description="Basic fitness tracking",
                price=0.0,
                features=["Basic workouts", "Progress tracking", "3 plugin trials"]
            ),
            "premium": SubscriptionPlan(
                plan_id="premium",
                name="Premium Plan",
                description="Advanced fitness coaching with premium plugins",
                price=9.99,
                features=["Unlimited workouts", "Advanced analytics", "All premium plugins", "Priority support"],
                trial_period_days=14
            ),
            "pro": SubscriptionPlan(
                plan_id="pro",
                name="Pro Plan",
                description="Professional coaching with custom programs",
                price=19.99,
                features=["Everything in Premium", "Custom workout programs", "1-on-1 coaching", "API access"],
                trial_period_days=7
            )
        }
    
    async def initialize(self) -> bool:
        """Initialize payment processor"""
        try:
            if self.stripe_enabled:
                # Test Stripe connection
                await self._test_stripe_connection()
                
                # Setup subscription plans in Stripe
                await self._setup_stripe_plans()
            
            return True
        except Exception as e:
            self.logger.error(f"Payment processor initialization failed: {e}")
            return False
    
    async def create_customer(self, user_id: str, email: str, name: str = None) -> Optional[str]:
        """Create customer in payment system"""
        try:
            if self.stripe_enabled:
                customer = stripe.Customer.create(
                    email=email,
                    name=name,
                    metadata={"user_id": user_id}
                )
                
                customer_id = customer.id
                self.logger.info(f"✅ Stripe customer created: {customer_id}")
            else:
                # Mock customer creation
                customer_id = f"cust_mock_{user_id}_{int(datetime.now().timestamp())}"
                self.logger.info(f"✅ Mock customer created: {customer_id}")
            
            # Store customer mapping
            self.customers[user_id] = {
                "customer_id": customer_id,
                "email": email,
                "name": name,
                "created_at": datetime.now().isoformat()
            }
            
            return customer_id
            
        except Exception as e:
            self.logger.error(f"Customer creation failed: {e}")
            return None
    
    async def create_plugin_payment(self, user_id: str, plugin_id: str, amount: float, 
                                  currency: str = "USD") -> Optional[PaymentTransaction]:
        """Create payment for plugin purchase"""
        try:
            transaction_id = f"txn_{user_id}_{plugin_id}_{int(datetime.now().timestamp())}"
            
            transaction = PaymentTransaction(
                transaction_id=transaction_id,
                user_id=user_id,
                payment_type=PaymentType.PLUGIN_PURCHASE,
                amount=amount,
                currency=currency,
                plugin_id=plugin_id
            )
            
            if self.stripe_enabled:
                # Get or create customer
                customer_id = await self._get_or_create_customer(user_id)
                if not customer_id:
                    return None
                
                # Create payment intent
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),  # Convert to cents
                    currency=currency.lower(),
                    customer=customer_id,
                    metadata={
                        "user_id": user_id,
                        "plugin_id": plugin_id,
                        "transaction_id": transaction_id
                    },
                    description=f"Plugin purchase: {plugin_id}"
                )
                
                transaction.stripe_payment_intent_id = payment_intent.id
                transaction.stripe_customer_id = customer_id
                
            # Store transaction
            self.transactions[transaction_id] = transaction
            
            # Save to database if available
            if self.db_manager:
                await self._save_transaction_db(transaction)
            
            self.logger.info(f"✅ Plugin payment created: {transaction_id}")
            return transaction
            
        except Exception as e:
            self.logger.error(f"Plugin payment creation failed: {e}")
            return None
    
    async def create_subscription_payment(self, user_id: str, plan_id: str) -> Optional[Dict[str, Any]]:
        """Create subscription payment"""
        try:
            plan = self.subscription_plans.get(plan_id)
            if not plan:
                self.logger.error(f"Subscription plan not found: {plan_id}")
                return None
            
            if plan.price == 0:
                # Free plan - no payment needed
                return await self._create_free_subscription(user_id, plan_id)
            
            if self.stripe_enabled:
                # Get or create customer
                customer_id = await self._get_or_create_customer(user_id)
                if not customer_id:
                    return None
                
                # Create subscription
                subscription_data = {
                    "customer": customer_id,
                    "items": [{"price": plan.stripe_price_id}],
                    "payment_behavior": "default_incomplete",
                    "expand": ["latest_invoice.payment_intent"],
                    "metadata": {
                        "user_id": user_id,
                        "plan_id": plan_id
                    }
                }
                
                if plan.trial_period_days > 0:
                    subscription_data["trial_period_days"] = plan.trial_period_days
                
                subscription = stripe.Subscription.create(**subscription_data)
                
                return {
                    "subscription_id": subscription.id,
                    "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                    "status": subscription.status,
                    "trial_end": subscription.trial_end
                }
            else:
                # Mock subscription
                subscription_id = f"sub_mock_{user_id}_{plan_id}_{int(datetime.now().timestamp())}"
                
                return {
                    "subscription_id": subscription_id,
                    "client_secret": f"pi_mock_{subscription_id}_secret",
                    "status": "trialing" if plan.trial_period_days > 0 else "active",
                    "trial_end": (datetime.now() + timedelta(days=plan.trial_period_days)).timestamp() if plan.trial_period_days > 0 else None
                }
                
        except Exception as e:
            self.logger.error(f"Subscription payment creation failed: {e}")
            return None
    
    async def confirm_payment(self, transaction_id: str, payment_method_id: str = None) -> bool:
        """Confirm payment completion"""
        try:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                self.logger.error(f"Transaction not found: {transaction_id}")
                return False
            
            if self.stripe_enabled and transaction.stripe_payment_intent_id:
                # Confirm payment intent
                if payment_method_id:
                    stripe.PaymentIntent.confirm(
                        transaction.stripe_payment_intent_id,
                        payment_method=payment_method_id
                    )
                
                # Get latest status
                payment_intent = stripe.PaymentIntent.retrieve(transaction.stripe_payment_intent_id)
                
                if payment_intent.status == "succeeded":
                    transaction.status = PaymentStatus.COMPLETED
                elif payment_intent.status == "failed":
                    transaction.status = PaymentStatus.FAILED
                else:
                    transaction.status = PaymentStatus.PROCESSING
            else:
                # Mock payment confirmation
                transaction.status = PaymentStatus.COMPLETED
            
            transaction.updated_at = datetime.now().isoformat()
            
            # Update database
            if self.db_manager:
                await self._save_transaction_db(transaction)
            
            # Process payment completion
            if transaction.status == PaymentStatus.COMPLETED:
                await self._process_payment_completion(transaction)
            
            return transaction.status == PaymentStatus.COMPLETED
            
        except Exception as e:
            self.logger.error(f"Payment confirmation failed: {e}")
            return False
    
    async def process_refund(self, transaction_id: str, amount: float = None, reason: str = None) -> bool:
        """Process payment refund"""
        try:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                self.logger.error(f"Transaction not found: {transaction_id}")
                return False
            
            if transaction.status != PaymentStatus.COMPLETED:
                self.logger.error(f"Cannot refund non-completed transaction: {transaction_id}")
                return False
            
            refund_amount = amount or transaction.amount
            
            if self.stripe_enabled and transaction.stripe_payment_intent_id:
                # Create refund in Stripe
                refund = stripe.Refund.create(
                    payment_intent=transaction.stripe_payment_intent_id,
                    amount=int(refund_amount * 100) if amount else None,
                    reason=reason or "requested_by_customer"
                )
                
                if refund.status == "succeeded":
                    transaction.status = PaymentStatus.REFUNDED
                else:
                    return False
            else:
                # Mock refund
                transaction.status = PaymentStatus.REFUNDED
            
            transaction.updated_at = datetime.now().isoformat()
            
            # Update database
            if self.db_manager:
                await self._save_transaction_db(transaction)
            
            self.logger.info(f"✅ Refund processed: {transaction_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Refund processing failed: {e}")
            return False
    
    async def cancel_subscription(self, user_id: str, subscription_id: str, immediate: bool = False) -> bool:
        """Cancel user subscription"""
        try:
            if self.stripe_enabled:
                subscription = stripe.Subscription.retrieve(subscription_id)
                
                if immediate:
                    stripe.Subscription.delete(subscription_id)
                else:
                    stripe.Subscription.modify(
                        subscription_id,
                        cancel_at_period_end=True
                    )
                
                # Update local record
                if subscription_id in self.subscriptions:
                    self.subscriptions[subscription_id].status = SubscriptionStatus.CANCELLED
                    self.subscriptions[subscription_id].cancelled_at = datetime.now().isoformat()
            else:
                # Mock cancellation
                if subscription_id in self.subscriptions:
                    self.subscriptions[subscription_id].status = SubscriptionStatus.CANCELLED
                    self.subscriptions[subscription_id].cancelled_at = datetime.now().isoformat()
            
            self.logger.info(f"✅ Subscription cancelled: {subscription_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Subscription cancellation failed: {e}")
            return False
    
    async def handle_webhook(self, payload: str, signature: str) -> bool:
        """Handle Stripe webhook events"""
        try:
            if not self.stripe_enabled or not self.webhook_secret:
                self.logger.warning("Webhook handling not available")
                return False
            
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            # Handle different event types
            if event["type"] == "payment_intent.succeeded":
                await self._handle_payment_succeeded(event["data"]["object"])
            elif event["type"] == "payment_intent.payment_failed":
                await self._handle_payment_failed(event["data"]["object"])
            elif event["type"] == "customer.subscription.created":
                await self._handle_subscription_created(event["data"]["object"])
            elif event["type"] == "customer.subscription.updated":
                await self._handle_subscription_updated(event["data"]["object"])
            elif event["type"] == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event["data"]["object"])
            elif event["type"] == "invoice.payment_succeeded":
                await self._handle_invoice_payment_succeeded(event["data"]["object"])
            elif event["type"] == "invoice.payment_failed":
                await self._handle_invoice_payment_failed(event["data"]["object"])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Webhook handling failed: {e}")
            return False
    
    async def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID"""
        return self.transactions.get(transaction_id)
    
    async def get_user_transactions(self, user_id: str) -> List[PaymentTransaction]:
        """Get all transactions for a user"""
        user_transactions = []
        for transaction in self.transactions.values():
            if transaction.user_id == user_id:
                user_transactions.append(transaction)
        
        return sorted(user_transactions, key=lambda x: x.created_at, reverse=True)
    
    async def get_user_subscription(self, user_id: str) -> Optional[CustomerSubscription]:
        """Get active subscription for user"""
        for subscription in self.subscriptions.values():
            if (subscription.user_id == user_id and 
                subscription.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]):
                return subscription
        return None
    
    # Helper methods
    async def _test_stripe_connection(self):
        """Test Stripe API connection"""
        try:
            stripe.Account.retrieve()
        except Exception as e:
            raise Exception(f"Stripe connection test failed: {e}")
    
    async def _setup_stripe_plans(self):
        """Setup subscription plans in Stripe"""
        try:
            for plan in self.subscription_plans.values():
                if plan.price > 0 and not plan.stripe_price_id:
                    # Create price in Stripe
                    price = stripe.Price.create(
                        unit_amount=int(plan.price * 100),
                        currency=plan.currency.lower(),
                        recurring={"interval": plan.interval},
                        product_data={
                            "name": plan.name,
                            "description": plan.description
                        }
                    )
                    plan.stripe_price_id = price.id
                    
            self.logger.info("✅ Stripe plans setup completed")
            
        except Exception as e:
            self.logger.error(f"Stripe plans setup failed: {e}")
    
    async def _get_or_create_customer(self, user_id: str) -> Optional[str]:
        """Get existing customer or create new one"""
        if user_id in self.customers:
            return self.customers[user_id]["customer_id"]
        
        # Create mock customer for demo
        return await self.create_customer(user_id, f"user_{user_id}@example.com", f"User {user_id}")
    
    async def _create_free_subscription(self, user_id: str, plan_id: str) -> Dict[str, Any]:
        """Create free subscription (no payment required)"""
        subscription_id = f"sub_free_{user_id}_{int(datetime.now().timestamp())}"
        
        subscription = CustomerSubscription(
            subscription_id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now().isoformat(),
            current_period_end=(datetime.now() + timedelta(days=365)).isoformat()
        )
        
        self.subscriptions[subscription_id] = subscription
        
        return {
            "subscription_id": subscription_id,
            "status": "active",
            "message": "Free subscription activated"
        }
    
    async def _process_payment_completion(self, transaction: PaymentTransaction):
        """Process completed payment"""
        try:
            if transaction.payment_type == PaymentType.PLUGIN_PURCHASE:
                # Grant plugin access to user
                await self._grant_plugin_access(transaction.user_id, transaction.plugin_id)
            
            self.logger.info(f"✅ Payment completion processed: {transaction.transaction_id}")
            
        except Exception as e:
            self.logger.error(f"Payment completion processing failed: {e}")
    
    async def _grant_plugin_access(self, user_id: str, plugin_id: str):
        """Grant plugin access to user after successful payment"""
        # This would integrate with the plugin licensing system
        self.logger.info(f"✅ Plugin access granted: {plugin_id} to user {user_id}")
    
    async def _save_transaction_db(self, transaction: PaymentTransaction):
        """Save transaction to database"""
        if self.db_manager:
            try:
                transaction_data = asdict(transaction)
                # Convert enum values to strings
                transaction_data["payment_type"] = transaction.payment_type.value
                transaction_data["status"] = transaction.status.value
                
                # This would save to the database
                self.logger.debug(f"Transaction saved to database: {transaction.transaction_id}")
            except Exception as e:
                self.logger.error(f"Database save failed: {e}")
    
    # Webhook handlers
    async def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment webhook"""
        transaction_id = payment_intent["metadata"].get("transaction_id")
        if transaction_id and transaction_id in self.transactions:
            transaction = self.transactions[transaction_id]
            transaction.status = PaymentStatus.COMPLETED
            transaction.updated_at = datetime.now().isoformat()
            
            await self._process_payment_completion(transaction)
    
    async def _handle_payment_failed(self, payment_intent):
        """Handle failed payment webhook"""
        transaction_id = payment_intent["metadata"].get("transaction_id")
        if transaction_id and transaction_id in self.transactions:
            transaction = self.transactions[transaction_id]
            transaction.status = PaymentStatus.FAILED
            transaction.updated_at = datetime.now().isoformat()
    
    async def _handle_subscription_created(self, subscription):
        """Handle subscription created webhook"""
        user_id = subscription["metadata"].get("user_id")
        plan_id = subscription["metadata"].get("plan_id")
        
        if user_id and plan_id:
            sub_record = CustomerSubscription(
                subscription_id=subscription["id"],
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus(subscription["status"]),
                current_period_start=datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
                current_period_end=datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
                stripe_subscription_id=subscription["id"]
            )
            
            self.subscriptions[subscription["id"]] = sub_record
    
    async def _handle_subscription_updated(self, subscription):
        """Handle subscription updated webhook"""
        subscription_id = subscription["id"]
        if subscription_id in self.subscriptions:
            sub_record = self.subscriptions[subscription_id]
            sub_record.status = SubscriptionStatus(subscription["status"])
            sub_record.updated_at = datetime.now().isoformat()
    
    async def _handle_subscription_deleted(self, subscription):
        """Handle subscription deleted webhook"""
        subscription_id = subscription["id"]
        if subscription_id in self.subscriptions:
            sub_record = self.subscriptions[subscription_id]
            sub_record.status = SubscriptionStatus.CANCELLED
            sub_record.cancelled_at = datetime.now().isoformat()
    
    async def _handle_invoice_payment_succeeded(self, invoice):
        """Handle successful invoice payment"""
        subscription_id = invoice.get("subscription")
        if subscription_id and subscription_id in self.subscriptions:
            sub_record = self.subscriptions[subscription_id]
            sub_record.status = SubscriptionStatus.ACTIVE
            sub_record.updated_at = datetime.now().isoformat()
    
    async def _handle_invoice_payment_failed(self, invoice):
        """Handle failed invoice payment"""
        subscription_id = invoice.get("subscription")
        if subscription_id and subscription_id in self.subscriptions:
            sub_record = self.subscriptions[subscription_id]
            sub_record.status = SubscriptionStatus.PAST_DUE
            sub_record.updated_at = datetime.now().isoformat()

# Factory function
def create_payment_processor(stripe_secret_key: str = None, webhook_secret: str = None, db_manager=None) -> PaymentProcessor:
    """Create payment processor with configuration"""
    if stripe_secret_key is None:
        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    if webhook_secret is None:
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    return PaymentProcessor(stripe_secret_key, webhook_secret, db_manager)

# Usage example
async def test_payment_processor():
    """Test payment processor"""
    processor = create_payment_processor()
    await processor.initialize()
    
    # Test plugin purchase
    transaction = await processor.create_plugin_payment(
        user_id="test_user",
        plugin_id="golf_pro",
        amount=12.99
    )
    
    if transaction:
        print(f"Payment created: {transaction.transaction_id}")
        
        # Confirm payment
        success = await processor.confirm_payment(transaction.transaction_id)
        print(f"Payment confirmed: {success}")

if __name__ == "__main__":
    asyncio.run(test_payment_processor())