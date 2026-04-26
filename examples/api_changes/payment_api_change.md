# API Change: Payment Processing Status

## Changed Endpoint

`POST /payments/process`

## Change Summary

The payment processing API now returns `pending_confirmation` when the external provider request times out.

The provider may send a delayed callback later to confirm the final transaction result.

The frontend payment status display depends on the backend transaction status.

Duplicate requests should not deduct user balance multiple times.

## QA Concern

This change may affect idempotency, provider callback handling, user-facing status display, and reconciliation.
