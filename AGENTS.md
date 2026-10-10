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
- Follow the existing stack: Django, Django REST Framework, server-rendered templates, vanilla JS in `src/gym_journal/static/`, Tailwind Play CDN, uv, Ruff, and pytest. Follow existing function-based views, manual `request.POST` + `full_clean()`, and DRF serializers. Do not add a SPA, Preact, React, TypeScript, Node toolchain, or form library unless asked.
- Write idiomatic JavaScript. Use async functions, object and array destructuring, nullish coalescing, and functional composition where they make intent clearer; avoid clever or overly chained expressions that are harder to read. JS here is small IIFEs in `src/gym_journal/static/` and does not call `/api/v1/`.
- Write idiomatic Python. Use type hints, decorators, and comprehensions where they make intent clearer; prefer a straightforward loop or explicit code when it is easier to understand. Use type hints where they already appear; do not introduce mypy unless asked.

## Tests

- Write tests for meaningful behavior and outcomes, not to mirror implementation details.
- Stub as little as practical. Prefer exercising real collaborators when that keeps the test clear and focused.
- When a test uses stubbed data, assert how the subject processes that data. Do not test or assert the return value of a stubbed API method itself; that value is defined by the test setup, not produced by the code under test.
- Keep tests readable and focused on one behavior so failures make the problem clear.
- Put tests in `src/gym_journal/tests/` using `django.test.TestCase` / `APITestCase` and helpers from `helpers.py`.
- Verify with `uv run pytest` (and `uv run ruff check .` when Python changed). Tests use in-memory SQLite and do not need Postgres.
- Do not invent an E2E/Playwright suite; this repo has none.

## Product

- Gym Journal is a private workout logger: one active workout per user, set logging (weight/reps or timed duration), workout history, and a shared exercise library.
- There is no public signup. Provision users via `createsuperuser` or Django admin.
- Muscle and exercise data is shared; workouts and sets belong to the signed-in user and must not leak across accounts.
- One active workout per user (`Workout.start`). Timed sets require duration (5–900 seconds); non-timed sets require reps.
- The primary UI is server-rendered Django templates. `/api/v1/` is a token API for external clients. When changing workout or exercise rules, keep web and API aligned or call out existing gaps instead of silently widening them.
- Keep user-facing copy short, direct, and in English.
- Do not invent signup, social, or public-discovery features. `robots.txt` disallows indexing.
- When a product decision is unclear, follow README, privacy/terms templates, and tests.

## Domain

- Web views auto-close inactive workouts after 90 minutes (`close_inactive_workouts`); the API does not.
- Web can edit sets; the API can delete a set on the active workout but has no set-update endpoint.
- Do not introduce a repository layer or `{success, data, error}` API envelope. This app uses the ORM and ordinary DRF JSON.

## Agent Work

- Keep changes focused and explain meaningful tradeoffs.
- Verify changes with relevant checks when the task calls for verification; report what was run and any limits. When verification was needed, report `uv run pytest` / `ruff`.
- Do not invent seed, curriculum, or exercise lists. Edit `src/gym_journal/seed_data.py` only when asked.
