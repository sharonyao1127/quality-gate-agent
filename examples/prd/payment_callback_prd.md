# Provider Payment Callback Upgrade

Business Domain: payment
Changed Components: payment callback service, transaction status updater, merchant notification service

## Background

We are introducing a new provider callback flow for payment transactions.
The provider may send delayed callback events after the merchant page has already shown a pending status.
The new flow will be launched to selected merchants first, then expanded to more traffic.

## Proposed Behavior

- Provider callback updates the transaction status.
- Merchant notification is sent after callback processing.
- Users can see pending, completed, or failed status on the order page.

## Open Questions

- Retry behavior is still being discussed with the provider.
- The exact timeout rule is not finalized.
- Reconciliation ownership will be confirmed before launch.

## Rollout

The new flow will be enabled for a small merchant cohort next week.
