# Design red flags

Screen the sketch before accepting it. A red flag is a reason to revise or reject the shape.

## Shallow module

A shallow module exposes a large interface while hiding little complexity. Judge depth by the capability and policy hidden behind the public surface relative to the size of that surface. Prefer a simple interface backed by substantial behavior.

Do not confuse a deep module with a deep call chain. A deep call chain scatters understanding across layers. A deep module concentrates capability behind one interface.

Look for these signs:

- Callers coordinate several methods to complete one operation.
- Public options expose internal stages or implementation choices.
- Learning the interface does not save the caller from learning the implementation.

## Information leakage

Information leakage makes multiple modules depend on the same internal decision. A representation, policy, or protocol detail appears in more than one place, so changing it requires coordinated edits.

Public re-exports of transport or wire types are leakage. Parse external data into domain types behind the interface. Keep storage schemas, framework objects, and protocol details private.

## Temporal decomposition

Temporal decomposition organizes modules by execution order instead of the knowledge they own. Separate load, validate, transform, and save stages often repeat one representation and its invariants across several boundaries.

Group code around domain knowledge and ownership. Methods that run at different times can still belong to one module when they protect the same decisions.

## Pass-through method

A pass-through method forwards the same arguments to another method with the same shape. It adds a layer without hiding complexity.

Remove it or move responsibility to the module that can complete the operation. Keep a forwarding boundary only when it adds policy, adaptation, or a distinct abstraction.

## Split ownership

More than one module writes the same state or keeps its own copy of it. An agent that edits one writer can't see the others, so their rules diverge.

Give each piece of state one owner. Other modules read it or ask the owner to change it.

## Two ways to do one task

The design supports more than one way to do the same task. An agent copies whichever way it finds first, so every way keeps gaining callers.

Keep one way. Move callers off the others and delete them in the same change.

## Importable internals

A caller can import a module's internals. An agent takes the shortest path that compiles, so it imports them directly and they become part of the interface.

Make internals unreachable from outside the module, so an import from outside fails the build.

## Hand-synced list

Two or more places list the same items, and adding an item means editing every list. An agent that sees one list updates only that one.

Keep one list and derive the others from it. If a list can't be derived, make the build fail when the lists disagree.

## Out of scope

The sketch changes behavior the task did not ask for, often sold as "this also closes a gap we have today". An agent
that reads the sketch takes the extra change as part of the plan and asks the user to settle it, so the task grows
one question at a time.

Take it out of the shape, and report it as a problem outside the task: its own change or a Linear card,
never a question to settle inside this task. When the task names what it owns, everything else is out of scope.

Judge scope against the task as the user stated it, never against the constraints the rationale restates in its
Problem section. A constraint that says a flow "stays" or "keeps working" means leave that flow's code unchanged; it
is not a license to redesign the flow around the change. Moving or tightening an existing gate, rule or check counts
as a behavior change even when the rationale calls it an invariant. Today's behavior of an out-of-scope flow is the
answer for the sketch, so it raises no question for the user: a value that flow reads keeps what it has today.

Example: a task to remove an integration came back with a sketch that also moved an approval gate another team owns.
