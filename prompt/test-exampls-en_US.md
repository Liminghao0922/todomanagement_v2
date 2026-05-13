Here are notes from today's meeting. Please extract the action items, check our past similar todos for hour estimates, and propose tasks for me to create.

---
Project Sync - Q2 Platform Migration
Attendees: Me, Sarah (PM), Raj (Backend Lead), Mei (Frontend)
Date: 2026-05-13

Discussion:
- Sarah confirmed the deadline for the API gateway cutover is end of May.
- Raj raised concerns about the auth service; he needs to refactor the JWT validation
  logic to support the new token format. Estimated this is non-trivial.
- Mei will update the login page and the settings page to call the new gateway URLs.
  She also wants to add a feature flag so we can roll back quickly.
- I agreed to write the migration runbook and document the rollback procedure
  before next Tuesday.
- We need a load test against the new gateway before going live. Raj suggested
  reusing the k6 scripts from the last migration. Owner TBD.
- Sarah will set up a status dashboard in Grafana for the cutover window — low
  priority but nice to have.

Next steps: confirm task list and estimates by EOD Friday.
---

For each action item:
1. Title + short description
2. Suggested owner (if mentioned)
3. Priority (high/medium/low)
4. Use the estimate_hours tool to suggest estimatedHours based on similar past todos, and explain why
5. Note any dependencies between tasks

Then ask me to confirm before creating them.