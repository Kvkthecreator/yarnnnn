# ADR-030 Context Extraction - Frontend Testing Prompt

> **Purpose**: This prompt is designed to be pasted into the Claude Chrome browser extension to test the ADR-030 Context Extraction Methodology features through the YARNNN web interface.

---

## Testing Instructions

You are helping me test the YARNNN web application's context extraction features (ADR-030). Please navigate through the interface and test each feature systematically.

### Prerequisites
- User must be logged in to YARNNN
- User should have at least one integration connected (Gmail, Slack, or Notion preferred)
- User should have at least one deliverable created

---

## Test Checklist

### 1. Deliverable Settings Modal - Source Configuration

**Steps:**
1. Navigate to the Deliverables page
2. Click on any deliverable to open its detail view
3. Click the Settings (gear) icon to open the Deliverable Settings Modal
4. Look for the "Sources" section

**Verify:**
- [ ] Sources section is visible in the modal
- [ ] "Add Source" button is present
- [ ] Existing sources (if any) are displayed

**Add Integration Source Test:**
1. Click "Add Source"
2. Select "Integration" as the source type
3. Select a provider (Gmail, Slack, or Notion)

**Verify Scope Configuration UI:**
- [ ] Extraction mode selector appears (Delta vs Fixed Window buttons)
- [ ] Default mode is "Delta" (highlighted/selected)
- [ ] Clicking "Fixed Window" selects that mode instead
- [ ] Fallback days / Window size dropdown appears
- [ ] Options include: 1 day, 3 days, 7 days, 14 days, 30 days
- [ ] Default value is 7 days
- [ ] Max items dropdown appears
- [ ] Options include: 50, 100, 200, 500
- [ ] Default value is 200

**Verify Labels:**
- [ ] Delta mode shows "Fallback days" label for the days dropdown
- [ ] Fixed Window mode shows "Window size" label for the days dropdown

### 2. Source Display in Modal

**Steps:**
1. Add an integration source with specific scope settings
2. Save the source
3. Observe how it appears in the sources list

**Verify:**
- [ ] Source displays with provider icon (Gmail/Slack/Notion)
- [ ] Source query/label is shown
- [ ] Scope information is displayed (e.g., "delta, 7 days fallback, max 200")
- [ ] Edit button allows modifying the source
- [ ] Delete/remove button works

### 3. Deliverable Run with Integration Sources

**Steps:**
1. Create or use a deliverable with an integration source
2. Trigger a manual run (if available) or wait for scheduled run
3. Check the version details after completion

**Verify:**
- [ ] Deliverable runs without errors
- [ ] Version is created with status progression (draft → staged or approved)
- [ ] If source_fetch_summary is visible, it shows:
  - sources_total count
  - sources_succeeded count
  - sources_failed count (should be 0 for success)
  - delta_mode_used indicator
  - time_range_start and time_range_end

### 4. Source Freshness Indicators (if implemented in UI)

**Steps:**
1. Navigate to a deliverable with integration sources
2. Look for freshness/staleness indicators

**Verify:**
- [ ] Sources show "Fresh" or "Stale" status
- [ ] Last fetched date/time is displayed
- [ ] Items fetched count is shown
- [ ] Stale threshold appears to be around 7 days

### 5. Delta vs Fixed Window Behavior

**Steps:**
1. Create two deliverables with the same integration source
2. Configure one with Delta mode, one with Fixed Window mode
3. Run both deliverables
4. Compare the results

**Verify for Delta mode:**
- [ ] First run fetches data based on fallback_days
- [ ] Subsequent runs fetch data since last_run_at
- [ ] Content should reflect only new data since last run

**Verify for Fixed Window mode:**
- [ ] Every run fetches data for the specified recency_days
- [ ] Content scope is consistent across runs

### 6. Error Handling

**Steps:**
1. Try adding a source for an integration that's not connected
2. Observe the error handling

**Verify:**
- [ ] Appropriate error message is shown
- [ ] UI doesn't break or crash
- [ ] User can still use other features

---

## Expected Behaviors Summary

| Feature | Expected Behavior |
|---------|------------------|
| Scope Mode Toggle | Delta/Fixed Window buttons toggle selection |
| Days Dropdown | Shows 1, 3, 7, 14, 30 options |
| Max Items Dropdown | Shows 50, 100, 200, 500 options |
| Source Display | Shows provider, query, and scope config |
| Deliverable Run | Fetches integration data based on scope |
| Freshness Tracking | Shows last fetch time and item counts |

---

## Reporting Issues

If you find issues, note:
1. The exact steps to reproduce
2. What you expected to happen
3. What actually happened
4. Any error messages (console or UI)
5. Browser and version

---

## Notes for Tester

- The scope configuration UI was added in Phase 5 of ADR-030
- Caching (Phase 6) means repeated fetches within 15 minutes may use cached data
- Haiku extraction (Phase 6) filters large content automatically
- Parallel fetching (Phase 6) makes multi-source deliverables faster

---

*This testing prompt covers ADR-030 Context Extraction Methodology implementation. Last updated: 2026-02-07*
