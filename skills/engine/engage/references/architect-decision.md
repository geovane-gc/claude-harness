Decide whether the change needs the **architect** skill, weighing `task.md`, the how's answer and,
in a bug fix, the cause.

- **Architect:** a shape chosen now is costly to change later: a type, a contract, a boundary,
  stored data.
- **Engineer directly:** the code already sets the shape, such as a version pin, a rename, or a fix
  or an extract inside one function or module.

Write the decision and its reason as a `decision` in the trail. Without the architect, make each
smaller choice left open (a field's type, a name) to fit the code that will read it, and write it
as a `decision` too.

When you put a product question to a person and its answer changes what gets built (the scope, a
contract, which service owns the data), wait for the answer before running the architect, and
design on it. Start a 30-minute timer (`sleep 1800` in Bash with `run_in_background`). Until the
answer comes, do only the work that holds under every answer, and check for the answer each time
the run wakes. When the timer fires with no answer, run the architect on the defaults sent with the
question, write each one as a `decision` in the trail, and tell the user which defaults it took.
