---
name: principle-record-before-side-effect
description: "Apply when code calls something outside the service that cannot be taken back: a payment, a signature, an order placed with a provider, a payout, a message sent. Write the record a retry will find before the call, derive the idempotency key from the entity, move status by compare-and-set, bound every retry, and treat an unconfirmed outcome as unknown."
disable-model-invocation: true
---

# Record Before Side Effect

Money that left cannot be called back. A retry, a redelivery or a crash between two lines is the
normal case, so the code is right only when each of them ends with the funds moved once.

- **Record first.** Persist the entity, in the state that says "about to call", before the external
  call. A retry that finds it resumes; a retry that finds nothing calls again.
- **Derive the key.** The idempotency key comes from the entity (`<purpose>-<entityId>`), never a
  fresh random value per attempt, so the provider answers a retry with the first outcome.
- **Compare and set.** A status changes only from the value the code read, in one write. A read
  followed by a separate write is a race with the redelivered copy of the same message.
- **Bound the retry.** Every loop that calls out has a maximum and a terminal state. A call that
  always fails, retried forever, is a bill and an alert storm.
- **Unknown is not failed.** A timeout or an ambiguous error after the call may have moved the
  money. Record it as unknown and let reconciliation read the provider; marking it failed invites a
  second send.
- **Prove it twice.** The test delivers the same message twice, or crashes between record and
  call, and asserts one side effect.
