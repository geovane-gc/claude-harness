# Types

Pick the first row that describes the change. Only feat, fix, perf, refactor and revert cut a release, so a change that must reach production (code, config that goes into the image, a dependency, a migration, a deploy file) is one of them, and a change that ships nothing is none of them.
A breaking change adds ! after the scope: feat(api)!: …

| Type     | The change…                                                                | Example                                          |
|----------|----------------------------------------------------------------------------|--------------------------------------------------|
| feat     | adds behavior a user or caller can see                                     | feat(account): refuse a second account per owner |
| fix      | corrects wrong behavior, or must ship with no new behavior (dependency, config) | fix(security): pin jackson 3 to 3.1.7       |
| perf     | makes the same behavior faster or lighter                                  | perf(query): read balances in one round trip     |
| refactor | changes structure, not behavior                                            | refactor(payment): move the gateway to infra     |
| revert   | undoes an earlier commit                                                   | revert: feat(account): refuse a second account   |
| test     | adds or fixes tests only                                                   | test(account): cover the duplicate owner case    |
| docs     | changes documentation only                                                 | docs(claude): add the commands and done rule     |
| build    | changes the build, nothing that ships                                      | build: add detekt, ktlint and Konsist            |
| ci       | changes CI configuration                                                   | ci: run the integration tests on every PR        |
| style    | changes formatting only, not meaning                                       | style(account): apply the formatter              |
| chore    | anything else that does not ship: tooling, repo hygiene, agent files       | chore(claude): load the repo context at start   |
