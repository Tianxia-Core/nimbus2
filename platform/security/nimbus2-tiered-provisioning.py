#!/usr/bin/env python3
# ffp: FFP-NIMBUS2-NIMBUS2-TIERED-PROVISION io-edge python
"""
NIMBUS² Intelligent Tiered Provisioning System
Dynamic free tier based on user categorization
"""

import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class UserTier(Enum):
    STARTER = 1
    GROWTH = 2
    BUSINESS = 3
    ENTERPRISE = 4

@dataclass
class UserProfile:
    user_id: str
    company_size: int
    use_case: str
    budget: float
    tier: UserTier
    engagement_score: float

class IntelligentTiering:
    """
    Intelligent Tiered Provisioning
    Dynamic free tier based on user categorization
    """
    
    TIER_CONFIG = {
        UserTier.STARTER: {
            "name": "Starter",
            "price": 0,
            "requests_per_day": 100,
            "countries": 1,
            "features": ["basic_serp", "single_proxy"],
            "description": "Individual users, limited access"
        },
        UserTier.GROWTH: {
            "name": "Growth",
            "price": 49,
            "requests_per_day": 1000,
            "countries": 5,
            "features": ["advanced_serp", "proxy_rotation", "5_countries"],
            "description": "Small teams, expanded access"
        },
        UserTier.BUSINESS: {
            "name": "Business",
            "price": 199,
            "requests_per_day": 10000,
            "countries": 10,
            "features": ["full_proxy", "research_tools", "api_access"],
            "description": "Mid-size companies, full access"
        },
        UserTier.ENTERPRISE: {
            "name": "Enterprise",
            "price": 999,
            "requests_per_day": -1,  # Unlimited
            "countries": -1,  # All
            "features": ["unlimited", "custom_integration", "support"],
            "description": "Large enterprises, unlimited access"
        }
    }
    
    def categorize_user(self, company_size: int, use_case: str, budget: float) -> UserTier:
        """Categorize user based on onboarding data"""
        if company_size < 10:
            return UserTier.STARTER
        elif company_size < 100:
            return UserTier.GROWTH
        elif company_size < 1000:
            return UserTier.BUSINESS
        else:
            return UserTier.ENTERPRISE
    
    def get_tier_config(self, tier: UserTier) -> Dict:
        """Get configuration for tier"""
        return self.TIER_CONFIG.get(tier, self.TIER_CONFIG[UserTier.STARTER])
    
    def adjust_tier(self, user: UserProfile) -> UserTier:
        """Dynamically adjust tier based on engagement"""
        if user.engagement_score > 0.8 and user.tier.value < UserTier.ENTERPRISE.value:
            # High engagement - upgrade
            new_tier = UserTier(user.tier.value + 1)
            print(f"Upgrading {user.user_id} to {new_tier.name}")
            return new_tier
        elif user.engagement_score < 0.2 and user.tier.value > UserTier.STARTER.value:
            # Low engagement - offer support
            print(f"Low engagement for {user.user_id} - offering support")
            return user.tier
        return user.tier
    
    def generate_onboarding_form(self) -> Dict:
        """Generate onboarding form questions"""
        return {
            "company_size": {
                "type": "number",
                "options": ["1-10", "10-100", "100-1000", "1000+"],
                "required": True
            },
            "use_case": {
                "type": "select",
                "options": ["SERP Scraping", "Data Collection", "Privacy", "Other"],
                "required": True
            },
            "budget": {
                "type": "select",
                "options": ["< $100/mo", "$100-500/mo", "$500-2000/mo", "$2000+/mo"],
                "required": True
            },
            "technical_requirements": {
                "type": "multiselect",
                "options": ["API Access", "Proxy Rotation", "Research Tools", "Custom Integration"],
                "required": False
            }
        }
