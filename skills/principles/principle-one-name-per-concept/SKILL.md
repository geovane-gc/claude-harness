---
name: principle-one-name-per-concept
description: "Apply when naming a field, parameter, event attribute, column or log key that carries something the system already names somewhere else. One concept keeps one name and one shape on every surface."
disable-model-invocation: true
---

# One Name Per Concept

A concept keeps the name and the shape it already has on every surface it crosses: request, response, event, stored document, log line and doc. Public or internal makes no difference: a reader who meets the value in two places must see that it is the same thing.

- Before naming a field, find what the same value is called elsewhere in the system and use that name.
- When two surfaces disagree, converge all of them on one name.
- When a rename breaks a consumer, sequence it: change the consumers first, then the producer.
