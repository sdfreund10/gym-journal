# Working Guidelines

## Code

The most important quality of written code is simplicity and readability. Write code so a person can understand what it does by reading it, without having to trace unnecessary indirection or infer hidden behavior.

- Prefer concise, well-named methods and functions. Names should communicate intent; avoid cryptic abbreviations and generic names.
- Give each function a focused responsibility and make its name match what it does. Extract helpers when they clarify the flow, not merely to shorten a function.
- Let the caller choose the behavior. When functionality has distinct paths, have the caller branch to clearly named methods instead of passing a flag or mode parameter that changes what one method does.
- Keep interfaces small. Add parameters, configuration switches, and public methods only when a current caller needs them.
- Avoid unnecessary indirection. Keep behavior direct and easy to trace; add a layer only when it makes the code clearer or serves a concrete framework or product need.
- Keep side effects apparent in the code's flow where practical. Follow framework conventions when they intentionally manage effects, and make those effects understandable in the surrounding code.
- Put code in well-named, appropriately sized files. Keep related responsibilities together, but split files and objects before they become difficult to navigate or understand. Avoid god objects and giant files.
- Prefer the simplest design that meets the current need. Do not add layers, abstractions, or dependencies without a concrete benefit.
- Start with the expected path. Add edge-case handling and defensive error paths when a real, observed, or required case calls for them; speculative handling adds complexity and makes behavior harder to understand.
- Apply YAGNI: implement current requirements, not hypothetical future features or flexibility. Add extension points only when a present need justifies them.
- Watch for code smells such as long methods, oversized classes, duplication, dead code, speculative generality, and excessive coupling. Use [Refactoring.Guru's catalog](https://refactoring.guru/refactoring/smells) as a diagnostic guide; address a smell when doing so makes the code easier to understand or change, not by applying refactorings mechanically.
- Follow the existing stack and conventions: Django and Django REST Framework, Preact and TypeScript, Ruff, and the configured project tooling.
- Write idiomatic JavaScript and TypeScript. Use async functions, object and array destructuring, nullish coalescing, and functional composition where they make intent clearer; avoid clever or overly chained expressions that are harder to read.
- Write idiomatic Python. Use type hints, decorators, and comprehensions where they make intent clearer; prefer a straightforward loop or explicit code when it is easier to understand.

## Tests

- Write tests for meaningful behavior and outcomes, not to mirror implementation details.
- Stub as little as practical. Prefer exercising real collaborators when that keeps the test clear and focused.
- When a test uses stubbed data, assert how the subject processes that data. Do not test or assert the return value of a stubbed API method itself; that value is defined by the test setup, not produced by the code under test.
- Keep tests readable and focused on one behavior so failures make the problem clear.

## Product

- Keep juzi focused on traditional Chinese vocabulary practice in its three established directions: pinyin to English, English to Chinese, and Chinese to English.
- Preserve the private household use case, admin-provisioned accounts, English app chrome, and same-origin session authentication.
- Do not invent product behavior where `PRODUCT.md` marks a decision as undecided. Do not fabricate vocabulary, curriculum, testimonials, or usage claims.
- Keep user-facing copy short, direct, and in English. Chinese belongs in study content.

## Agent Work

- Keep changes focused and explain meaningful tradeoffs.
- Verify changes with relevant checks when the task calls for verification; report what was run and any limits.
