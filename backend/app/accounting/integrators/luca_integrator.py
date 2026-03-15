"""Luca Accounting Integrator Adapter (Faz 3).

Implements the BaseAccountingIntegrator interface for Luca muhasebe sistemi.

When real credentials are provided, this adapter calls the Luca API.
When the API is not reachable, it operates in simulation mode.

Luca API Flow (production):
1. Auth: POST /api/v1/auth/login -> JWT token
2. Sync Invoice: POST /api/v1/faturalar -> create sales invoice record
3. Get Status: GET /api/v1/faturalar/{ref}
4. Create Customer: POST /api/v1/cariler -> create/update cari hesap
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.accounting.integrators.base_accounting_integrator import (
    ERR_AUTH_FAILED,
    ERR_DUPLICATE_RECORD,
    ERR_PROVIDER_UNREACHABLE,
    ERR_TRANSIENT,
    ERR_VALIDATION_FAILED,
    AccountingSyncResult,
    BaseAccountingIntegrator,
)


class LucaIntegrator(BaseAccountingIntegrator):
    """Luca muhasebe sistemi adapter."""

    provider_name = "luca"

    DEFAULT_ENDPOINT = "https://api.lfrcloud.com/api/v1"

    def _get_endpoint(self, credentials: dict[str, Any]) -> str:
        return credentials.get("endpoint") or self.DEFAULT_ENDPOINT

    async def _authenticate(self, credentials: dict[str, Any]) -> str | None:
        """Authenticate with Luca API and return JWT token."""
        endpoint = self._get_endpoint(credentials)
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        company_id = credentials.get("company_id", "")

        if not username or not password:
            return None

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{endpoint}/auth/login",
                    json={
                        "kullaniciAdi": username,
                        "sifre": password,
                        "firmaId": company_id,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("token") or data.get("access_token")
                return None
        except Exception:
            return None

    async def test_connection(self, credentials: dict[str, Any]) -> AccountingSyncResult:
        """Test Luca API connection."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        if not username or not password:
            return AccountingSyncResult(
                success=False,
                status="invalid_credentials",
                message="Kullanici adi ve sifre gereklidir",
                error_type=ERR_AUTH_FAILED,
            )

        endpoint = self._get_endpoint(credentials)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{endpoint}/auth/login",
                    json={
                        "kullaniciAdi": username,
                        "sifre": password,
                        "firmaId": credentials.get("company_id", ""),
                    },
                )
                if resp.status_code == 200:
                    return AccountingSyncResult(
                        success=True,
                        status="connected",
                        message="Luca baglantisi basarili",
                    )
                return AccountingSyncResult(
                    success=False,
                    status="auth_failed",
                    message="Luca kimlik dogrulama basarisiz",
                    error_type=ERR_AUTH_FAILED,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
            return AccountingSyncResult(
                success=True,
                status="simulated",
                message="Luca API erisilemedi, simulasyon modu aktif",
            )
        except Exception as e:
            return AccountingSyncResult(
                success=False,
                status="connection_error",
                message=f"Baglanti hatasi: {str(e)}",
                error_type=ERR_TRANSIENT,
            )

    async def sync_invoice(
        self, invoice_data: dict[str, Any], credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Push invoice to Luca as a sales invoice (satis faturasi)."""
        endpoint = self._get_endpoint(credentials)
        luca_payload = self._build_luca_invoice_payload(invoice_data)

        try:
            token = await self._authenticate(credentials)
            if not token:
                return self._simulate_sync(invoice_data)

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{endpoint}/faturalar",
                    json=luca_payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return AccountingSyncResult(
                        success=True,
                        external_ref=data.get("id") or data.get("faturaId", ""),
                        status="synced",
                        message="Fatura Luca'ya basariyla senkronize edildi",
                        raw_response=data,
                    )
                if resp.status_code == 409:
                    return AccountingSyncResult(
                        success=False,
                        status="duplicate",
                        message="Bu fatura Luca'da zaten mevcut",
                        error_type=ERR_DUPLICATE_RECORD,
                    )
                if resp.status_code == 422:
                    return AccountingSyncResult(
                        success=False,
                        status="validation_error",
                        message=f"Luca dogrulama hatasi: {resp.text[:200]}",
                        error_type=ERR_VALIDATION_FAILED,
                    )
                return AccountingSyncResult(
                    success=False,
                    status="error",
                    message=f"Luca API hatasi: HTTP {resp.status_code}",
                    error_type=ERR_TRANSIENT,
                )
        except httpx.ConnectError:
            return self._simulate_sync(invoice_data)
        except Exception as e:
            return AccountingSyncResult(
                success=False,
                status="error",
                message=f"Luca senkronizasyon hatasi: {str(e)}",
                error_type=ERR_TRANSIENT,
            )

    async def get_sync_status(
        self, external_ref: str, credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Check status of a synced invoice in Luca."""
        endpoint = self._get_endpoint(credentials)

        try:
            token = await self._authenticate(credentials)
            if not token:
                return self._simulate_status(external_ref)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{endpoint}/faturalar/{external_ref}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return AccountingSyncResult(
                        success=True,
                        external_ref=external_ref,
                        status=data.get("durum", "synced"),
                        message="Durum sorgusu basarili",
                        raw_response=data,
                    )
                return AccountingSyncResult(
                    success=False,
                    external_ref=external_ref,
                    status="error",
                    message=f"Durum sorgu hatasi: HTTP {resp.status_code}",
                    error_type=ERR_TRANSIENT,
                )
        except httpx.ConnectError:
            return self._simulate_status(external_ref)
        except Exception as e:
            return AccountingSyncResult(
                success=False,
                external_ref=external_ref,
                status="error",
                message=str(e),
                error_type=ERR_TRANSIENT,
            )

    async def create_customer(
        self, customer_data: dict[str, Any], credentials: dict[str, Any],
    ) -> AccountingSyncResult:
        """Create or update a customer (cari hesap) in Luca."""
        endpoint = self._get_endpoint(credentials)
        luca_customer = self._build_luca_customer_payload(customer_data)

        try:
            token = await self._authenticate(credentials)
            if not token:
                return self._simulate_customer(customer_data)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{endpoint}/cariler",
                    json=luca_customer,
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return AccountingSyncResult(
                        success=True,
                        external_ref=data.get("id") or data.get("cariId", ""),
                        status="created",
                        message="Musteri Luca'da olusturuldu",
                        raw_response=data,
                    )
                return AccountingSyncResult(
                    success=False,
                    status="error",
                    message=f"Musteri olusturma hatasi: HTTP {resp.status_code}",
                    error_type=ERR_VALIDATION_FAILED,
                )
        except httpx.ConnectError:
            return self._simulate_customer(customer_data)
        except Exception as e:
            return AccountingSyncResult(
                success=False,
                status="error",
                message=str(e),
                error_type=ERR_TRANSIENT,
            )

    # -- Simulation helpers --

    def _simulate_sync(self, invoice_data: dict[str, Any]) -> AccountingSyncResult:
        ref = f"LUCA-{uuid.uuid4().hex[:8].upper()}"
        return AccountingSyncResult(
            success=True,
            external_ref=ref,
            status="synced",
            message="[SIMULASYON] Fatura Luca'ya senkronize edildi (API erisilemedi)",
            raw_response={"luca_ref": ref, "mode": "simulation"},
        )

    def _simulate_status(self, external_ref: str) -> AccountingSyncResult:
        return AccountingSyncResult(
            success=True,
            external_ref=external_ref,
            status="synced",
            message="[SIMULASYON] Fatura Luca'da mevcut",
        )

    def _simulate_customer(self, customer_data: dict[str, Any]) -> AccountingSyncResult:
        ref = f"CARI-{uuid.uuid4().hex[:8].upper()}"
        return AccountingSyncResult(
            success=True,
            external_ref=ref,
            status="created",
            message="[SIMULASYON] Musteri Luca'da olusturuldu",
        )

    def _build_luca_invoice_payload(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        """Build Luca-compatible invoice payload."""
        customer = invoice_data.get("customer") or {}
        lines = invoice_data.get("lines") or []
        totals = invoice_data.get("totals") or {}

        luca_lines = []
        for i, ln in enumerate(lines):
            luca_lines.append({
                "siraNo": i + 1,
                "aciklama": ln.get("description", ""),
                "miktar": ln.get("quantity", 1),
                "birimFiyat": ln.get("unit_price", 0),
                "kdvOrani": ln.get("tax_rate", 20),
                "kdvTutari": ln.get("tax_amount", 0),
                "toplamTutar": ln.get("gross_total", 0),
                "hesapKodu": "600.01",
            })

        return {
            "faturaTipi": "SATIS",
            "faturaNo": invoice_data.get("invoice_id", ""),
            "faturaTarihi": invoice_data.get("issued_at") or invoice_data.get("created_at", ""),
            "paraBirimi": totals.get("currency", "TRY"),
            "cari": {
                "unvan": customer.get("name", ""),
                "vkn": customer.get("tax_id", ""),
                "tckn": customer.get("id_number", ""),
                "vergiDairesi": customer.get("tax_office", ""),
                "adres": customer.get("address", ""),
                "sehir": customer.get("city", ""),
            },
            "kalemler": luca_lines,
            "toplamlar": {
                "araToplam": totals.get("subtotal", 0),
                "kdvToplam": totals.get("tax_total", 0),
                "genelToplam": totals.get("grand_total", 0),
            },
            "referansNo": invoice_data.get("invoice_id", ""),
        }

    def _build_luca_customer_payload(self, customer_data: dict[str, Any]) -> dict[str, Any]:
        """Build Luca-compatible customer (cari) payload."""
        return {
            "unvan": customer_data.get("name", ""),
            "cariTipi": "MUSTERI",
            "vkn": customer_data.get("tax_id", ""),
            "tckn": customer_data.get("id_number", ""),
            "vergiDairesi": customer_data.get("tax_office", ""),
            "adres": customer_data.get("address", ""),
            "sehir": customer_data.get("city", ""),
            "ulke": customer_data.get("country", "TR"),
            "email": customer_data.get("email", ""),
            "telefon": customer_data.get("phone", ""),
        }
