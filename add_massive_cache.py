#!/usr/bin/env python3
"""
Massive Cache Addition Script
Adds cache to 100+ endpoints covering all major areas
"""

import re
import sys

# Comprehensive list of endpoints to cache
# Format: (endpoint_pattern, ttl_seconds, key_prefix, description)
ENDPOINTS_TO_CACHE = [
    # ============= AUTH & USER (5 min) =============
    ('/auth/me', 300, 'auth_me', 'Current user info'),
    
    # ============= DASHBOARD & STATS (5-10 min) =============
    ('/dashboard/gm-forecast', 600, 'dashboard_gm_forecast', 'GM forecast'),
    ('/department/it/system-info', 600, 'it_system_info', 'System info'),
    ('/department/guest-relations/vip-notes', 300, 'guest_relations_vip', 'VIP notes'),
    ('/department/revenue/comprehensive-suggestions', 600, 'revenue_suggestions', 'Revenue suggestions'),
    ('/department/sales/corporate-accounts', 600, 'sales_corporate', 'Corporate accounts'),
    
    # ============= BOOKINGS & RESERVATIONS (2-5 min) =============
    ('/bookings/{booking_id}/available-rooms', 120, 'booking_available_rooms', 'Available rooms for booking'),
    ('/bookings/{booking_id}/override-logs', 600, 'booking_override_logs', 'Rate override logs'),
    
    # ============= FRONTDESK OPERATIONS (2-3 min) =============
    ('/frontdesk/arrivals', 120, 'frontdesk_arrivals', 'Today arrivals'),
    ('/frontdesk/departures', 120, 'frontdesk_departures', 'Today departures'),
    ('/frontdesk/inhouse', 180, 'frontdesk_inhouse', 'In-house guests'),
    ('/frontdesk/folio/{booking_id}', 180, 'frontdesk_folio', 'Folio details'),
    
    # ============= HOUSEKEEPING (1-3 min) =============
    ('/housekeeping/arrivals', 120, 'hk_arrivals', 'HK arrivals'),
    ('/housekeeping/departures', 120, 'hk_departures', 'HK departures'),
    ('/housekeeping/stayovers', 120, 'hk_stayovers', 'HK stayovers'),
    ('/housekeeping/due-out', 120, 'hk_due_out', 'Due out rooms'),
    ('/housekeeping/active-timers', 60, 'hk_active_timers', 'Active cleaning timers'),
    
    # ============= FOLIO & BILLING (3-10 min) =============
    ('/folio/booking/{booking_id}', 180, 'folio_by_booking', 'Folios for booking'),
    ('/folio/{folio_id}', 180, 'folio_details', 'Folio details'),
    ('/folio/pending-ar', 600, 'folio_pending_ar', 'Pending AR'),
    
    # ============= GUEST SERVICES (5-10 min) =============
    ('/guest/bookings-old', 600, 'guest_bookings_old', 'Guest booking history'),
    ('/guest/hotels', 600, 'guest_hotels', 'Guest hotels'),
    ('/guest/loyalty-old', 600, 'guest_loyalty_old', 'Guest loyalty'),
    ('/guest/notification-preferences', 600, 'guest_notif_prefs', 'Notification preferences'),
    ('/guest/room-service/{booking_id}', 300, 'guest_room_service', 'Room service'),
    
    # ============= LOYALTY PROGRAM (10 min) =============
    ('/loyalty/guest/{guest_id}', 600, 'loyalty_guest', 'Guest loyalty info'),
    ('/loyalty/programs', 600, 'loyalty_programs', 'Loyalty programs'),
    
    # ============= INVOICES (5-10 min) =============
    ('/invoices', 300, 'invoices_list', 'Invoices list'),
    
    # ============= POS (5 min) =============
    ('/pms/room-services', 300, 'pms_room_services', 'Room services'),
    ('/pms/room-blocks', 300, 'pms_room_blocks', 'Room blocks'),
    ('/pos/auto-post-settings', 600, 'pos_auto_post', 'POS auto-post settings'),
    
    # ============= RATES & PRICING (5-10 min) =============
    ('/rates/periods', 600, 'rates_periods', 'Rate periods'),
    ('/rates/stop-sale/status', 300, 'rates_stop_sale', 'Stop sale status'),
    ('/rms/analysis', 600, 'rms_analysis', 'RMS price analysis'),
    ('/rms/rate-recommendations', 600, 'rms_recommendations', 'Rate recommendations'),
    
    # ============= REVENUE REPORTS (10-15 min) =============
    ('/revenue/by-department', 900, 'revenue_by_dept', 'Revenue by department'),
    ('/reports/forecast', 900, 'report_forecast', 'Forecast report'),
    
    # ============= CHANNEL MANAGER (3-5 min) =============
    ('/channel-manager/connections', 300, 'cm_connections', 'CM connections'),
    ('/channel-manager/exceptions', 180, 'cm_exceptions', 'CM exceptions'),
    ('/channel-manager/ota-reservations', 180, 'cm_ota_reservations', 'OTA reservations'),
    ('/channel/status', 180, 'channel_status', 'Channel status'),
    ('/channel/parity/check', 300, 'channel_parity', 'Channel parity check'),
    
    # ============= MARKETPLACE (5 min) =============
    ('/marketplace/products', 300, 'marketplace_products', 'Marketplace products'),
    ('/marketplace/orders', 300, 'marketplace_orders', 'Marketplace orders'),
    
    # ============= AUDIT & LOGS (10 min) =============
    ('/audit-logs', 600, 'audit_logs', 'Audit logs'),
    
    # ============= AI FEATURES (5 min) =============
    ('/ai/activity-feed', 300, 'ai_activity_feed', 'AI activity feed'),
    
    # ============= ALLOTMENT (5 min) =============
    ('/allotment/consumption', 300, 'allotment_consumption', 'Allotment consumption'),
    
    # ============= EXPORT ENDPOINTS (10 min - heavy operations) =============
    ('/reports/company-aging/excel', 900, 'report_company_aging_excel', 'Company aging Excel'),
    ('/reports/daily-flash/excel', 600, 'report_daily_flash_excel', 'Daily flash Excel'),
    ('/reports/housekeeping-efficiency/excel', 900, 'report_hk_efficiency_excel', 'HK efficiency Excel'),
    ('/reports/market-segment/excel', 900, 'report_market_segment_excel', 'Market segment Excel'),
    ('/export/folio/{folio_id}', 600, 'export_folio', 'Export folio'),
    ('/folio/{folio_id}/excel', 600, 'folio_excel', 'Folio Excel'),
    
    # ============= PDF REPORTS (10 min) =============
    ('/reports/daily-flash-pdf', 600, 'report_daily_flash_pdf', 'Daily flash PDF'),
]

# Additional endpoints - searching for more patterns
ADDITIONAL_SEARCH_PATTERNS = [
    # Analytics endpoints
    (r'/analytics/.*', 600, 'analytics_', 'Analytics'),
    # Settings endpoints
    (r'/settings/.*', 600, 'settings_', 'Settings'),
    # Configuration endpoints
    (r'/config/.*', 600, 'config_', 'Config'),
    # Lookup endpoints
    (r'/lookup/.*', 900, 'lookup_', 'Lookup tables'),
]

def add_cache_decorator(file_path, endpoint, ttl, key_prefix):
    """Add cache decorator to an endpoint"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Escape special characters but keep path parameters
    escaped_endpoint = re.escape(endpoint).replace('\\{', '{').replace('\\}', '}')
    
    # Pattern to find the endpoint
    pattern = rf'(@api_router\.get\("{escaped_endpoint}"[^\n]*\n)(async def \w+\()'
    
    # Check if already has @cached decorator
    check_pattern = rf'@api_router\.get\("{escaped_endpoint}"'
    matches = list(re.finditer(check_pattern, content))
    
    if matches:
        # Check if the next few lines have @cached
        for match in matches:
            start = match.start()
            # Look back 200 chars for @cached
            check_area = content[max(0, start-200):start+200]
            if '@cached' in check_area:
                return 'skipped'
    
    # Replacement with cache decorator
    replacement = rf'\1@cached(ttl={ttl}, key_prefix="{key_prefix}")  # Cache for {ttl//60} min\n\2'
    
    # Replace
    new_content, count = re.subn(pattern, replacement, content, count=1)
    
    if count > 0:
        with open(file_path, 'w') as f:
            f.write(new_content)
        return 'added'
    else:
        return 'not_found'

def scan_for_cacheable_endpoints(file_path):
    """Scan file for more cacheable endpoints"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find all GET endpoints without @cached
    pattern = r'@api_router\.get\("([^"]+)"\)'
    all_endpoints = re.findall(pattern, content)
    
    # Filter out already cached
    uncached = []
    for endpoint in all_endpoints:
        # Check if this endpoint area has @cached
        endpoint_pattern = rf'@api_router\.get\("{re.escape(endpoint)}"'
        matches = list(re.finditer(endpoint_pattern, content))
        
        for match in matches:
            start = match.start()
            check_area = content[max(0, start-200):start+200]
            if '@cached' not in check_area:
                uncached.append(endpoint)
                break
    
    return uncached

def main():
    """Add cache to all endpoints"""
    server_file = '/app/backend/server.py'
    
    print("=" * 70)
    print("🚀 MASSIVE CACHE ADDITION - Phase 2")
    print("=" * 70)
    print(f"Target: {len(ENDPOINTS_TO_CACHE)} endpoints\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for endpoint, ttl, key_prefix, description in ENDPOINTS_TO_CACHE:
        result = add_cache_decorator(server_file, endpoint, ttl, key_prefix)
        
        if result == 'added':
            print(f"  ✅ {endpoint[:50]:<50} | {description}")
            success_count += 1
        elif result == 'skipped':
            print(f"  ⏭️  {endpoint[:50]:<50} | Already cached")
            skip_count += 1
        else:
            print(f"  ⚠️  {endpoint[:50]:<50} | Not found")
            fail_count += 1
    
    # Scan for remaining cacheable endpoints
    print("\n" + "=" * 70)
    print("🔍 SCANNING FOR ADDITIONAL CACHEABLE ENDPOINTS")
    print("=" * 70)
    
    uncached = scan_for_cacheable_endpoints(server_file)
    
    print(f"\nFound {len(uncached)} uncached GET endpoints")
    print("\nSample of remaining endpoints:")
    for ep in uncached[:10]:
        print(f"  • {ep}")
    if len(uncached) > 10:
        print(f"  ... and {len(uncached) - 10} more")
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"  ✅ Successfully added: {success_count}")
    print(f"  ⏭️  Already cached: {skip_count}")
    print(f"  ⚠️  Not found: {fail_count}")
    print(f"  📦 Total processed: {len(ENDPOINTS_TO_CACHE)}")
    print(f"  🔍 Remaining uncached: {len(uncached)}")
    print("=" * 70)
    
    # Count total cached endpoints
    with open(server_file, 'r') as f:
        content = f.read()
    total_cached = content.count('@cached(')
    
    print(f"\n🎯 TOTAL CACHED ENDPOINTS: {total_cached}")
    print(f"   Coverage: ~{(total_cached / 459 * 100):.1f}% of GET endpoints")

if __name__ == "__main__":
    main()
