---
name: principle-test-behavior-not-implementation
description: "Apply when writing, changing or keeping a test. Call the code the way its users do and assert the exact result they see; rewrite or delete a test that would still pass with the code wrong."
disable-model-invocation: true
---

# Test Behavior, Not Implementation

A test calls the code as its users do and asserts the exact result they see. Rewrite or delete any test that would still pass if the code under test returned a wrong value or did nothing.

These shapes fail that check:

- Loose or no assertion: `shouldNotBeNull()`, `shouldNotThrowAny`, `size shouldBeGreaterThan 0`, or only the HTTP status when another path of the same call answers that status too.
- Call or absence only: `verify { mock.call() }` with no payload, `coVerify(exactly = 0)` alone, `shouldBeEmpty()` alone.
- Expected value computed by the code under test: `f(a) shouldBe f(a)`.
- Restated constant, config default, table row, or message string.
- Assertions on data the test built, with no call to the subject.

Fix: call the subject in the test body with one concrete input and assert the literal output or effect: the status together with the body field that tells this case from its neighbors (such as the error `code`), the stored document, the published event's payload. For a mock, assert the payload it received. For an absence, also assert the presence on another input. For a constant, test the mechanism that reads it with one input instead of restating the value.

Keep relation checks across rows (a key in two tables, a parent that exists).
