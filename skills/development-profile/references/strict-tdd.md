# Optional strict TDD and checkpoint workflow

Read this only when the user or project explicitly asks for strict test-first development, a coverage target, E2E coverage, or task-local git checkpoints. It does not change the default policy in `../SKILL.md`.

## RED / GREEN / REFACTOR

1. Add a test that expresses the requested behavior or reproduces the bug.
2. Run the relevant target and confirm that the new test executes and fails for the intended missing behavior or defect. A setup failure, missing dependency, syntax failure, or unrelated regression is not a valid RED signal.
3. Implement the smallest change that makes the same test GREEN.
4. Refactor only while the relevant target remains green.

Complete one observable behavior through this cycle before drafting the next batch of tests. Avoid writing an entire speculative test suite before any behavior runs.

Choose the existing public interface that can expose the real failure, including multiple callers or persistence when the defect depends on them. State what that test boundary catches and misses; ask for clarification only if the choice changes acceptance scope or cost. Derive expected results from a requirement, a worked example, or an independent known-good value, rather than repeating the implementation's calculation inside the assertion.

Example behavior-oriented test:

```typescript
it('returns a validation error for an invalid limit', async () => {
  const response = await GET(new NextRequest('http://localhost/api/items?limit=invalid'))
  expect(response.status).toBe(400)
})
```

Use a compile-time RED only when the new test directly references the missing contract and compilation is the intended signal.

For a component, assert user-visible behavior rather than internal state:

```typescript
it('calls onClick when enabled', async () => {
  const onClick = vi.fn()
  render(<Button onClick={onClick}>Save</Button>)
  await userEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(onClick).toHaveBeenCalledOnce()
})
```

For an endpoint, cover the contract at its boundary: a valid request, an invalid input path, and any requested authorization or persistence behavior. Mock external systems at the module boundary only when using an isolated unit test; an integration test should use the project's approved test implementation instead.

## Optional coverage and E2E gates

If a project declares a coverage threshold, use its configured coverage command and report the measured result. Add E2E coverage only for user flows, browser behavior, or project acceptance criteria that make it relevant. Do not invent a global target.

Example E2E assertion for an explicitly required flow:

```typescript
test('user can submit the form', async ({ page }) => {
  await page.goto('/create')
  await page.getByLabel('Name').fill('Test item')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText('Created')).toBeVisible()
})
```

## Optional git checkpoints

When explicit task-local checkpoints are requested, make a checkpoint only after evidence exists and confirm it is reachable from the current branch:

- `test: add reproducer for <behavior>` after a valid RED;
- `fix: <behavior>` after the same test is GREEN;
- optional `refactor: clean up <behavior>` after verification.

These commits document an agreed workflow; they are not a prerequisite to ordinary code changes.
