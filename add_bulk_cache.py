#!/usr/bin/env python3
"""
Bulk Cache Addition Script
Adds cache decorators to multiple endpoints at once
"""

import re

# Endpoints to cache with their TTL values
ENDPOINTS_TO_CACHE = [
    # Format: (endpoint_pattern, ttl_seconds, key_prefix)
    
    # Lists (2-5 minutes) - Frequently accessed
    ('/pms/rooms/availability', 120, 'rooms_availability'),
    ('/housekeeping/rooms', 120, 'housekeeping_rooms_list'),
    ('/maintenance/tasks', 180, 'maintenance_tasks'),
    ('/tasks/kanban', 180, 'tasks_kanban'),
    ('/tasks/dashboard', 300, 'tasks_dashboard'),
    
    # Guest related (5 minutes)
    ('/guest/bookings', 300, 'guest_bookings_history'),
    ('/guests/{guest_id}/profile-enhanced', 300, 'guest_profile_enhanced'),
    ('/guests/{guest_id}/profile-complete', 300, 'guest_profile_complete'),
    
    # Reports (10-15 minutes) - Less frequently updated
    ('/reports/company-aging', 900, 'report_company_aging'),
    ('/reports/finance-snapshot', 600, 'report_finance_snapshot'),
    ('/reports/cost-summary', 600, 'report_cost_summary'),
    ('/reports/housekeeping-efficiency', 600, 'report_hk_efficiency'),
    ('/accounting/reports/profit-loss', 900, 'report_profit_loss'),
    
    # Statistics (10 minutes)
    ('/invoices/stats', 600, 'invoices_stats'),
    ('/housekeeping/staff/{staff_id}/detailed-stats', 600, 'staff_detailed_stats'),
    
    # Room operations (2-3 minutes)
    ('/frontdesk/available-rooms', 120, 'frontdesk_available_rooms'),
    ('/frontdesk/rooms-with-filters', 180, 'frontdesk_rooms_filtered'),
    ('/rooms/{room_id}/details-enhanced', 180, 'room_details_enhanced'),
    
    # Bookings (3 minutes)
    ('/frontdesk/search-bookings', 180, 'frontdesk_search_bookings'),
    ('/deluxe/group-bookings', 300, 'deluxe_group_bookings'),
    ('/sales/group-bookings', 300, 'sales_group_bookings'),
    
    # Mobile endpoints (1-2 minutes) - Real-time needed
    ('/housekeeping/mobile/my-tasks', 60, 'mobile_hk_my_tasks'),
    ('/housekeeping/mobile/sla-delayed-rooms', 120, 'mobile_hk_delayed_rooms'),
    ('/maintenance/mobile/tasks/filtered', 120, 'mobile_maintenance_tasks'),
    ('/frontoffice/mobile/available-rooms', 120, 'mobile_available_rooms'),
    
    # Finance (5-10 minutes)
    ('/finance/folios-filtered', 300, 'finance_folios_filtered'),
]

def add_cache_decorator(file_path, endpoint, ttl, key_prefix):
    """Add cache decorator to an endpoint"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Escape special characters in endpoint
    escaped_endpoint = re.escape(endpoint).replace('\\{', '{').replace('\\}', '}')
    
    # Pattern to find the endpoint
    pattern = rf'(@api_router\.get\("{escaped_endpoint}"\)[^\n]*\n)(async def \w+\()'
    
    # Replacement with cache decorator
    replacement = rf'\1@cached(ttl={ttl}, key_prefix="{key_prefix}")  # Cache for {ttl//60} min\n\2'
    
    # Check if already has @cached decorator
    if rf'@cached.*"{key_prefix}"' in content:
        print(f"  ⏭️  Skipped {endpoint} - already cached")
        return False
    
    # Replace
    new_content, count = re.subn(pattern, replacement, content, count=1)
    
    if count > 0:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"  ✅ Added cache to {endpoint} (TTL: {ttl}s)")
        return True
    else:
        print(f"  ⚠️  Not found: {endpoint}")
        return False

def main():
    """Add cache to all endpoints"""
    server_file = '/app/backend/server.py'
    
    print("=" * 70)
    print("🚀 BULK CACHE ADDITION")
    print("=" * 70)
    print(f"Target: {len(ENDPOINTS_TO_CACHE)} endpoints\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for endpoint, ttl, key_prefix in ENDPOINTS_TO_CACHE:
        result = add_cache_decorator(server_file, endpoint, ttl, key_prefix)
        if result is True:
            success_count += 1
        elif result is False:
            skip_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"  ✅ Successfully added: {success_count}")
    print(f"  ⏭️  Already cached: {skip_count}")
    print(f"  ⚠️  Not found: {fail_count}")
    print(f"  📦 Total endpoints: {len(ENDPOINTS_TO_CACHE)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
