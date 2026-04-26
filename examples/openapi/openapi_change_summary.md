# OpenAPI Change Summary

## Endpoint

`POST /payments/process`

## Contract Changes

- Response `status` enum changed.
- New status values added: `pending_confirmation`, `waiting_callback`.
- New required field added: `provider_request_id`.
- New response field added: `callback_required`.

## Potential Risk

- Existing clients may not handle new status values.
- Required field changes may break consumers.
- Callback-related fields may affect async processing and reconciliation.
