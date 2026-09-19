# Automatic marketplace booking reconciliation

The API lifespan starts the recovery worker automatically. It is dormant without
`SYROCE_BASE_URL`; it uses each record's organization to load that organization's
active encrypted marketplace credentials. No button or separate polling setting
is required. This is independent of the single-hotel B2B ARI polling service.

Only marketplace records still `pending` and at least two minutes old are eligible.
The worker checks up to 50 records per cycle, sleeps 60 seconds between cycles,
and schedules unresolved/error records for another attempt after five minutes.
These are minimum eligibility delays, not strict completion SLAs under load.
Existing pending records are eligible even without a reconciliation flag.

An atomic Mongo claim leases a record for two minutes. Final writes require the
same organization, pending status, unexpired lease and claim token. A process crash
leaves a lease that expires; application shutdown cancels the worker. A stale
worker cannot overwrite a newer claim or a booking already finalized by the
normal booking handler. The due-query index is created automatically.

## Fail-closed lookup

The worker only sends GET requests to PMS. It never creates, cancels, or resubmits
a reservation and never changes PNRs. The current marketplace API does not expose
an exact-reference lookup or pagination, so recovery uses its agency-scoped list
filtered by hotel and arrival date, followed by an authenticated detail lookup.

The complete list must contain exactly one reference match. Lists at the 500-row
cap are inconclusive. Hotel, agency, reference, dates, guest/contact information,
room type, occupancy and special requests must match. Detail summary and hotel
booking must agree on identity, supported status and financial fields. Only
consistent `confirmed` or `cancelled` outcomes are recovered automatically.

Empty/malformed results, duplicate PNRs, mismatched data, unknown statuses, missing
ledger entries, inactive credentials and network errors remain pending. Absence
from a list is never proof of rejection. This worker cannot repair a PMS booking
whose creation succeeded but whose marketplace ledger write failed; it stays
unresolved for investigation. It does not reconcile ambiguous cancellation of an
already-confirmed local record, or continuously synchronize all confirmed records.

## Traceability and validation

Records retain last check, next check, attempt count and last outcome. A bounded
history retains the last 20 check outcomes in the same atomic update. No guest
data, remote error body or API key is written into that history.

Validation uses mocked HTTP and database/client doubles; it does not establish
real Mongo concurrency or live PMS compatibility. Before release, verify a timed-out
successful booking, two simultaneous workers, lease expiry/restart, mismatched
organization, duplicate PNR, a missing ledger entry and loss of PMS connectivity
against a test environment. No PMS code or deployment is changed by this feature.
