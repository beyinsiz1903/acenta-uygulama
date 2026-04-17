# Event Catalog
> Auto-generated: 2026-04-17 15:43 UTC
> Source: `app/infrastructure/event_contracts.py`

| Event Type | Description | Cache Invalidation Targets |
|-----------|-------------|---------------------------|
| **b2b** | | |
| `b2b.partner.activated` | B2B partner aktif edildi | `dash_b2b_today`, `dash_admin_today` |
| `b2b.booking.created` | B2B kanalından rezervasyon | `dash_b2b_today`, `dash_admin_today`, `dash_kpi` |
| `b2b.offer.expired` | B2B teklifi süresi doldu | `dash_b2b_today` |
| **booking** | | |
| `booking.reservation.created` | Yeni rezervasyon oluşturuldu | `dash_admin_today`, `dash_agency_today`, `dash_hotel_today`, `dash_kpi` |
| `booking.reservation.updated` | Rezervasyon güncellendi (tarih, oda, fiyat vb.) | `dash_admin_today`, `dash_agency_today`, `dash_hotel_today` |
| `booking.reservation.cancelled` | Rezervasyon iptal edildi | `dash_admin_today`, `dash_agency_today`, `dash_hotel_today`, `dash_kpi` |
| `booking.reservation.confirmed` | Rezervasyon onaylandı | `dash_admin_today`, `dash_agency_today` |
| **dashboard** | | |
| `dashboard.summary.invalidated` | Dashboard özeti manuel olarak invalidate edildi | `dash_admin_today`, `dash_agency_today`, `dash_hotel_today`, `dash_b2b_today`, `dash_kpi` |
| **enterprise** | | |
| `enterprise.approval.requested` | Onay talebi oluşturuldu | `dash_admin_today` |
| `enterprise.approval.approved` | Onay verildi | `dash_admin_today` |
| `enterprise.approval.rejected` | Onay reddedildi | `dash_admin_today` |
| **finance** | | |
| `finance.payment.received` | Ödeme alındı | `dash_admin_today`, `dash_agency_today`, `dash_kpi` |
| `finance.payment.overdue` | Ödeme vadesi geçti | `dash_admin_today`, `dash_agency_today` |
| `finance.invoice.issued` | Fatura kesildi | `dash_admin_today` |
| **ops** | | |
| `ops.checkin.completed` | Misafir check-in yaptı | `dash_hotel_today` |
| `ops.checkout.completed` | Misafir check-out yaptı | `dash_hotel_today` |
| `ops.incident.created` | Yeni operasyonel olay / şikayet | `dash_admin_today` |
| `ops.task.completed` | Operasyonel görev tamamlandı | `dash_admin_today` |
| **pricing** | | |
| `pricing.rule.updated` | Fiyatlama kuralı güncellendi | `dash_admin_today` |

**Total**: 19 events across 7 domains

## Event Naming Convention

```
{domain}.{entity}.{action}
```

Examples: `booking.reservation.created`, `ops.checkin.completed`
