"""
Subscription & Pricing Models
Defines subscription tiers and feature access
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class SubscriptionTier(str, Enum):
    """Subscription tier levels"""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    ULTRA = "ultra"


class FeatureFlag(str, Enum):
    """Feature flags for different subscription tiers"""
    # Core PMS
    FRONT_DESK = "front_desk"
    HOUSEKEEPING = "housekeeping"
    BASIC_REPORTING = "basic_reporting"
    
    # Pro Features
    CHANNEL_MANAGER = "channel_manager"
    FOLIO_MANAGEMENT = "folio_management"
    NIGHT_AUDIT = "night_audit"
    MULTI_PROPERTY = "multi_property"
    ADVANCED_REPORTING = "advanced_reporting"
    
    # Enterprise Features
    REVENUE_MANAGEMENT = "revenue_management"
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    LOYALTY_PROGRAM = "loyalty_program"
    API_ACCESS = "api_access"
    WHITE_LABEL = "white_label"
    
    # Ultra Features (AI-Powered)
    AI_PRICING = "ai_pricing"
    AI_PERSONALIZATION = "ai_personalization"
    SMART_DOOR_LOCKS = "smart_door_locks"
    MARKETPLACE = "marketplace"
    ML_ANALYTICS = "ml_analytics"
    CUSTOM_INTEGRATIONS = "custom_integrations"


class SubscriptionPlan(BaseModel):
    """Subscription plan definition"""
    tier: SubscriptionTier
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    max_rooms: Optional[int] = None  # None = unlimited
    max_users: Optional[int] = None
    features: List[FeatureFlag]
    support_level: str  # email, priority, dedicated
    

# Define subscription plans
SUBSCRIPTION_PLANS: Dict[SubscriptionTier, SubscriptionPlan] = {
    SubscriptionTier.BASIC: SubscriptionPlan(
        tier=SubscriptionTier.BASIC,
        name="Basic",
        description="Essential PMS features for small hotels",
        price_monthly=99.0,
        price_yearly=990.0,  # 2 months free
        max_rooms=25,
        max_users=5,
        features=[
            FeatureFlag.FRONT_DESK,
            FeatureFlag.HOUSEKEEPING,
            FeatureFlag.BASIC_REPORTING
        ],
        support_level="email"
    ),
    
    SubscriptionTier.PRO: SubscriptionPlan(
        tier=SubscriptionTier.PRO,
        name="Pro",
        description="Advanced features for growing properties",
        price_monthly=299.0,
        price_yearly=2990.0,
        max_rooms=100,
        max_users=15,
        features=[
            FeatureFlag.FRONT_DESK,
            FeatureFlag.HOUSEKEEPING,
            FeatureFlag.BASIC_REPORTING,
            FeatureFlag.CHANNEL_MANAGER,
            FeatureFlag.FOLIO_MANAGEMENT,
            FeatureFlag.NIGHT_AUDIT,
            FeatureFlag.MULTI_PROPERTY,
            FeatureFlag.ADVANCED_REPORTING
        ],
        support_level="priority"
    ),
    
    SubscriptionTier.ENTERPRISE: SubscriptionPlan(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        description="Full-featured solution with revenue management",
        price_monthly=599.0,
        price_yearly=5990.0,
        max_rooms=None,  # Unlimited
        max_users=None,
        features=[
            FeatureFlag.FRONT_DESK,
            FeatureFlag.HOUSEKEEPING,
            FeatureFlag.BASIC_REPORTING,
            FeatureFlag.CHANNEL_MANAGER,
            FeatureFlag.FOLIO_MANAGEMENT,
            FeatureFlag.NIGHT_AUDIT,
            FeatureFlag.MULTI_PROPERTY,
            FeatureFlag.ADVANCED_REPORTING,
            FeatureFlag.REVENUE_MANAGEMENT,
            FeatureFlag.PREDICTIVE_MAINTENANCE,
            FeatureFlag.LOYALTY_PROGRAM,
            FeatureFlag.API_ACCESS,
            FeatureFlag.WHITE_LABEL
        ],
        support_level="dedicated"
    ),
    
    SubscriptionTier.ULTRA: SubscriptionPlan(
        tier=SubscriptionTier.ULTRA,
        name="Ultra",
        description="AI-powered hotel management with all features",
        price_monthly=999.0,
        price_yearly=9990.0,
        max_rooms=None,
        max_users=None,
        features=[
            # All features from Enterprise
            FeatureFlag.FRONT_DESK,
            FeatureFlag.HOUSEKEEPING,
            FeatureFlag.BASIC_REPORTING,
            FeatureFlag.CHANNEL_MANAGER,
            FeatureFlag.FOLIO_MANAGEMENT,
            FeatureFlag.NIGHT_AUDIT,
            FeatureFlag.MULTI_PROPERTY,
            FeatureFlag.ADVANCED_REPORTING,
            FeatureFlag.REVENUE_MANAGEMENT,
            FeatureFlag.PREDICTIVE_MAINTENANCE,
            FeatureFlag.LOYALTY_PROGRAM,
            FeatureFlag.API_ACCESS,
            FeatureFlag.WHITE_LABEL,
            # Ultra-exclusive features
            FeatureFlag.AI_PRICING,
            FeatureFlag.AI_PERSONALIZATION,
            FeatureFlag.SMART_DOOR_LOCKS,
            FeatureFlag.MARKETPLACE,
            FeatureFlag.ML_ANALYTICS,
            FeatureFlag.CUSTOM_INTEGRATIONS
        ],
        support_level="dedicated"
    )
}


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


def has_feature_access(tier: SubscriptionTier, feature: FeatureFlag) -> bool:
    """Check if a subscription tier has access to a feature"""
    plan = SUBSCRIPTION_PLANS.get(tier)
    if not plan:
        return False
    return feature in plan.features


def get_feature_comparison() -> Dict[str, Dict[SubscriptionTier, bool]]:
    """Get feature comparison across all tiers"""
    all_features = [
        FeatureFlag.FRONT_DESK,
        FeatureFlag.HOUSEKEEPING,
        FeatureFlag.BASIC_REPORTING,
        FeatureFlag.CHANNEL_MANAGER,
        FeatureFlag.FOLIO_MANAGEMENT,
        FeatureFlag.NIGHT_AUDIT,
        FeatureFlag.MULTI_PROPERTY,
        FeatureFlag.ADVANCED_REPORTING,
        FeatureFlag.REVENUE_MANAGEMENT,
        FeatureFlag.PREDICTIVE_MAINTENANCE,
        FeatureFlag.LOYALTY_PROGRAM,
        FeatureFlag.API_ACCESS,
        FeatureFlag.WHITE_LABEL,
        FeatureFlag.AI_PRICING,
        FeatureFlag.AI_PERSONALIZATION,
        FeatureFlag.SMART_DOOR_LOCKS,
        FeatureFlag.MARKETPLACE,
        FeatureFlag.ML_ANALYTICS,
        FeatureFlag.CUSTOM_INTEGRATIONS
    ]
    
    comparison = {}
    for feature in all_features:
        comparison[feature.value] = {
            tier: has_feature_access(tier, feature)
            for tier in SubscriptionTier
        }
    
    return comparison
