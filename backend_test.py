#!/usr/bin/env python3
"""
PR-UM5 Backend Validation Test
Turkish Review Request: PR-UM5 backend doğrulaması yap.

Test Requirements:
1. Cookie-compat login with agent@acenta.test / agent123
2. /api/auth/me returns tenant_id
3. /api/tenant/usage-summary?days=30 returns expected structure:
   - plan_label = Trial, is_trial = true
   - reservation.created = 70/100 → warning
   - report.generated = 17/20 → critical
   - export.generated = 10/10 → limit_reached
   - trial_conversion.recommended_plan_label = "Pro Plan"
4. Validate soft quota thresholds (70/85/100 logic)
5. Validate CTA fields are present
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://usage-metering.preview.emergentagent.com"
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"

class PR_UM5_BackendValidator:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PR-UM5-Backend-Test/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.tenant_id: Optional[str] = None
        self.test_results = []

    def log_test(self, test_name: str, passed: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"{status}: {test_name}")
        if not passed:
            print(f"   Details: {details}")

    def test_1_cookie_compat_login(self) -> bool:
        """Test 1: Cookie-compat login with agent@acenta.test"""
        print("\n=== Test 1: Cookie-Compat Login ===")
        
        try:
            # Perform login with X-Client-Platform: web for cookie mode
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            headers = {
                'X-Client-Platform': 'web',  # This triggers cookie mode
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers=headers
            )
            
            if response.status_code != 200:
                self.log_test("Cookie-compat login", False, 
                            f"Login failed with status {response.status_code}: {response.text}")
                return False
                
            login_resp = response.json()
            
            # Validate login response
            if 'auth_transport' not in login_resp:
                self.log_test("Cookie-compat login", False, 
                            "Missing auth_transport in login response")
                return False
                
            if login_resp['auth_transport'] != 'cookie_compat':
                self.log_test("Cookie-compat login", False, 
                            f"Expected auth_transport=cookie_compat, got {login_resp['auth_transport']}")
                return False
                
            # Check if cookies are set
            if 'Set-Cookie' not in response.headers and not response.cookies:
                self.log_test("Cookie-compat login", False, 
                            "No cookies set in cookie_compat mode")
                return False
                
            self.log_test("Cookie-compat login", True, 
                        f"Login successful with auth_transport={login_resp['auth_transport']}")
            return True
            
        except Exception as e:
            self.log_test("Cookie-compat login", False, f"Exception: {str(e)}")
            return False

    def test_2_auth_me_tenant_id(self) -> bool:
        """Test 2: /api/auth/me returns tenant_id"""
        print("\n=== Test 2: Auth Me Tenant ID ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/auth/me")
            
            if response.status_code != 200:
                self.log_test("/api/auth/me tenant_id", False, 
                            f"Auth/me failed with status {response.status_code}: {response.text}")
                return False
                
            auth_data = response.json()
            
            # Validate tenant_id is present
            if 'tenant_id' not in auth_data:
                self.log_test("/api/auth/me tenant_id", False, 
                            "tenant_id missing from /api/auth/me response")
                return False
                
            if not auth_data['tenant_id']:
                self.log_test("/api/auth/me tenant_id", False, 
                            "tenant_id is null or empty")
                return False
                
            self.tenant_id = auth_data['tenant_id']
            
            # Validate user email matches
            if auth_data.get('email') != TEST_EMAIL:
                self.log_test("/api/auth/me tenant_id", False, 
                            f"Email mismatch: expected {TEST_EMAIL}, got {auth_data.get('email')}")
                return False
                
            self.log_test("/api/auth/me tenant_id", True, 
                        f"tenant_id returned: {self.tenant_id}, email: {auth_data.get('email')}")
            return True
            
        except Exception as e:
            self.log_test("/api/auth/me tenant_id", False, f"Exception: {str(e)}")
            return False

    def test_3_usage_summary_structure(self) -> bool:
        """Test 3: /api/tenant/usage-summary structure validation"""
        print("\n=== Test 3: Usage Summary Structure ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("Usage summary structure", False, 
                            f"Usage summary failed with status {response.status_code}: {response.text}")
                return False
                
            usage_data = response.json()
            
            # Validate basic structure
            required_fields = ['plan_label', 'is_trial', 'period', 'metrics']
            missing_fields = [field for field in required_fields if field not in usage_data]
            
            if missing_fields:
                self.log_test("Usage summary structure", False, 
                            f"Missing required fields: {missing_fields}")
                return False
                
            # Validate metrics structure
            metrics = usage_data.get('metrics', {})
            required_metrics = ['reservation.created', 'report.generated', 'export.generated']
            missing_metrics = [metric for metric in required_metrics if metric not in metrics]
            
            if missing_metrics:
                self.log_test("Usage summary structure", False, 
                            f"Missing required metrics: {missing_metrics}")
                return False
                
            self.log_test("Usage summary structure", True, 
                        f"All required fields present. Plan: {usage_data.get('plan_label')}, Trial: {usage_data.get('is_trial')}")
            
            return True
            
        except Exception as e:
            self.log_test("Usage summary structure", False, f"Exception: {str(e)}")
            return False

    def test_4_trial_plan_validation(self) -> bool:
        """Test 4: Trial plan configuration validation"""
        print("\n=== Test 4: Trial Plan Validation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("Trial plan validation", False, 
                            f"Usage summary failed with status {response.status_code}")
                return False
                
            usage_data = response.json()
            
            # Check plan_label = Trial
            expected_plan_label = "Trial"
            actual_plan_label = usage_data.get('plan_label')
            
            if actual_plan_label != expected_plan_label:
                self.log_test("Trial plan validation", False, 
                            f"Expected plan_label='{expected_plan_label}', got '{actual_plan_label}'")
                return False
                
            # Check is_trial = true
            is_trial = usage_data.get('is_trial')
            if is_trial is not True:
                self.log_test("Trial plan validation", False, 
                            f"Expected is_trial=true, got {is_trial}")
                return False
                
            self.log_test("Trial plan validation", True, 
                        f"Trial configuration correct: plan_label='{actual_plan_label}', is_trial={is_trial}")
            return True
            
        except Exception as e:
            self.log_test("Trial plan validation", False, f"Exception: {str(e)}")
            return False

    def test_5_usage_thresholds_validation(self) -> bool:
        """Test 5: Usage thresholds and warning levels validation"""
        print("\n=== Test 5: Usage Thresholds Validation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("Usage thresholds validation", False, 
                            f"Usage summary failed with status {response.status_code}")
                return False
                
            usage_data = response.json()
            metrics = usage_data.get('metrics', {})
            
            # Expected thresholds per review request
            expected_thresholds = {
                'reservation.created': {'used': 70, 'limit': 100, 'warning_level': 'warning', 
                                     'message': 'Limitinize yaklaşıyorsunuz'},
                'report.generated': {'used': 17, 'limit': 20, 'warning_level': 'critical'},
                'export.generated': {'used': 10, 'limit': 10, 'warning_level': 'limit_reached',
                                   'message': 'Export limitiniz doldu. Planınızı yükselterek devam edebilirsiniz.'}
            }
            
            all_passed = True
            details = []
            
            for metric_name, expected in expected_thresholds.items():
                if metric_name not in metrics:
                    all_passed = False
                    details.append(f"Missing metric: {metric_name}")
                    continue
                    
                metric = metrics[metric_name]
                
                # Check used value
                if metric.get('used') != expected['used']:
                    all_passed = False
                    details.append(f"{metric_name}: expected used={expected['used']}, got {metric.get('used')}")
                
                # Check limit value
                if metric.get('limit') != expected['limit']:
                    all_passed = False
                    details.append(f"{metric_name}: expected limit={expected['limit']}, got {metric.get('limit')}")
                
                # Check warning level
                if metric.get('warning_level') != expected['warning_level']:
                    all_passed = False
                    details.append(f"{metric_name}: expected warning_level={expected['warning_level']}, got {metric.get('warning_level')}")
                
                # Check message if specified
                if 'message' in expected and metric.get('warning_message') != expected['message']:
                    all_passed = False
                    details.append(f"{metric_name}: expected message='{expected['message']}', got '{metric.get('warning_message')}'")
            
            if all_passed:
                self.log_test("Usage thresholds validation", True, 
                            "All metrics match expected thresholds and warning levels")
            else:
                self.log_test("Usage thresholds validation", False, 
                            "; ".join(details))
                
            return all_passed
            
        except Exception as e:
            self.log_test("Usage thresholds validation", False, f"Exception: {str(e)}")
            return False

    def test_6_cta_fields_validation(self) -> bool:
        """Test 6: CTA fields validation"""
        print("\n=== Test 6: CTA Fields Validation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("CTA fields validation", False, 
                            f"Usage summary failed with status {response.status_code}")
                return False
                
            usage_data = response.json()
            metrics = usage_data.get('metrics', {})
            
            # Check for CTA on report.generated (critical state)
            report_metric = metrics.get('report.generated', {})
            if not report_metric.get('upgrade_recommended'):
                self.log_test("CTA fields validation", False, 
                            "report.generated should have upgrade_recommended=true")
                return False
                
            # Check for CTA on export.generated (limit_reached state)  
            export_metric = metrics.get('export.generated', {})
            if not export_metric.get('upgrade_recommended'):
                self.log_test("CTA fields validation", False, 
                            "export.generated should have upgrade_recommended=true")
                return False
                
            # Check CTA label
            expected_cta = "Planları Görüntüle"
            if report_metric.get('cta_label') != expected_cta:
                self.log_test("CTA fields validation", False, 
                            f"Expected cta_label='{expected_cta}', got '{report_metric.get('cta_label')}'")
                return False
                
            self.log_test("CTA fields validation", True, 
                        f"CTA fields present: report and export have upgrade_recommended=true, cta_label='{expected_cta}'")
            return True
            
        except Exception as e:
            self.log_test("CTA fields validation", False, f"Exception: {str(e)}")
            return False

    def test_7_trial_conversion_validation(self) -> bool:
        """Test 7: Trial conversion recommendation validation"""
        print("\n=== Test 7: Trial Conversion Validation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("Trial conversion validation", False, 
                            f"Usage summary failed with status {response.status_code}")
                return False
                
            usage_data = response.json()
            
            # Check trial_conversion field exists
            trial_conversion = usage_data.get('trial_conversion')
            if not trial_conversion:
                self.log_test("Trial conversion validation", False, 
                            "trial_conversion field missing or empty")
                return False
                
            # Check show field
            if not trial_conversion.get('show'):
                self.log_test("Trial conversion validation", False, 
                            "trial_conversion.show should be true")
                return False
                
            # Check recommended_plan_label
            expected_plan_label = "Pro Plan"
            actual_plan_label = trial_conversion.get('recommended_plan_label')
            
            if actual_plan_label != expected_plan_label:
                self.log_test("Trial conversion validation", False, 
                            f"Expected recommended_plan_label='{expected_plan_label}', got '{actual_plan_label}'")
                return False
                
            self.log_test("Trial conversion validation", True, 
                        f"Trial conversion correct: show=true, recommended_plan_label='{actual_plan_label}'")
            return True
            
        except Exception as e:
            self.log_test("Trial conversion validation", False, f"Exception: {str(e)}")
            return False

    def test_8_soft_quota_logic_validation(self) -> bool:
        """Test 8: Soft quota threshold logic (70/85/100) validation"""
        print("\n=== Test 8: Soft Quota Logic Validation ===")
        
        try:
            response = self.session.get(f"{self.base_url}/api/tenant/usage-summary?days=30")
            
            if response.status_code != 200:
                self.log_test("Soft quota logic validation", False, 
                            f"Usage summary failed with status {response.status_code}")
                return False
                
            usage_data = response.json()
            metrics = usage_data.get('metrics', {})
            
            # Validate threshold logic
            threshold_validations = []
            
            # reservation.created: 70/100 = 70% -> warning (>= 70%)
            reservation = metrics.get('reservation.created', {})
            reservation_pct = (reservation.get('used', 0) / reservation.get('limit', 1)) * 100 if reservation.get('limit') else 0
            if reservation_pct >= 70 and reservation_pct < 85:
                if reservation.get('warning_level') == 'warning':
                    threshold_validations.append("reservation.created: 70% threshold -> warning ✅")
                else:
                    threshold_validations.append(f"reservation.created: 70% should be warning, got {reservation.get('warning_level')} ❌")
            
            # report.generated: 17/20 = 85% -> critical (>= 85%)  
            report = metrics.get('report.generated', {})
            report_pct = (report.get('used', 0) / report.get('limit', 1)) * 100 if report.get('limit') else 0
            if report_pct >= 85 and report_pct < 100:
                if report.get('warning_level') == 'critical':
                    threshold_validations.append("report.generated: 85% threshold -> critical ✅")
                else:
                    threshold_validations.append(f"report.generated: 85% should be critical, got {report.get('warning_level')} ❌")
            
            # export.generated: 10/10 = 100% -> limit_reached (>= 100%)
            export = metrics.get('export.generated', {})
            export_pct = (export.get('used', 0) / export.get('limit', 1)) * 100 if export.get('limit') else 0
            if export_pct >= 100:
                if export.get('warning_level') == 'limit_reached':
                    threshold_validations.append("export.generated: 100% threshold -> limit_reached ✅")
                else:
                    threshold_validations.append(f"export.generated: 100% should be limit_reached, got {export.get('warning_level')} ❌")
            
            all_passed = all("✅" in validation for validation in threshold_validations)
            
            self.log_test("Soft quota logic validation", all_passed, 
                        "; ".join(threshold_validations))
            return all_passed
            
        except Exception as e:
            self.log_test("Soft quota logic validation", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all validation tests"""
        print("🚀 Starting PR-UM5 Backend Validation")
        print(f"Base URL: {self.base_url}")
        print(f"Test Account: {TEST_EMAIL}")
        
        # Run tests in sequence
        tests = [
            self.test_1_cookie_compat_login,
            self.test_2_auth_me_tenant_id,
            self.test_3_usage_summary_structure,
            self.test_4_trial_plan_validation,
            self.test_5_usage_thresholds_validation,
            self.test_6_cta_fields_validation,
            self.test_7_trial_conversion_validation,
            self.test_8_soft_quota_logic_validation
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_func in tests:
            if test_func():
                passed_tests += 1
                
        # Final summary
        print("\n" + "="*50)
        print("📊 PR-UM5 Backend Validation Summary")
        print("="*50)
        
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"{status}: {result['test']}")
            if not result['passed']:
                print(f"   → {result['details']}")
        
        print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests PASSED! PR-UM5 backend validation successful.")
            return True
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) FAILED. See details above.")
            return False

def main():
    """Main execution function"""
    validator = PR_UM5_BackendValidator()
    
    try:
        success = validator.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()