# Deliverable Workflow E2E Test Prompt

> **For**: Claude in Chrome (browser-based testing)
> **Purpose**: Qualitative end-to-end testing of the deliverable creation, generation, and review workflow
> **App URL**: [Your YARNNN staging/local URL]

---

## Context for Claude

You are testing YARNNN, a productivity app that helps users create recurring "deliverables" - documents like status reports, stakeholder updates, and research briefs that get generated on a schedule using AI.

The app has a "Thinking Partner" (TP) - a conversational AI assistant that helps users set up and manage their deliverables through natural conversation.

---

## Test Scenario: Board Update for a Startup

### Your Persona

You are **Alex Chen**, a startup founder who:
- Runs a Series A fintech company called "PayFlow"
- Reports to a board of 4 investors quarterly
- Needs to send monthly informal updates between board meetings
- Prefers concise, metrics-forward communication
- Your lead investor is "Marcus Webb from Sequoia"

---

## Testing Instructions

### Phase 1: Initial Exploration (2-3 min)

1. **Land on the dashboard** - Observe:
   - What do you see first? Is it clear what this app does?
   - Are there any deliverables already? What's the visual hierarchy?
   - Note the TP bar at the bottom - what indicators do you see?

2. **Interact with TP** - Send a greeting:
   ```
   Hey, I'm new here. What can you help me with?
   ```
   - Does TP explain the app's purpose clearly?
   - Does it suggest next steps?

---

### Phase 2: Deliverable Creation Flow (5-7 min)

3. **Initiate creation** - Tell TP:
   ```
   I need to send monthly updates to my board of directors. Can you help me set that up?
   ```

   **Observe**:
   - Does TP ask clarifying questions or jump straight to creation?
   - Does it understand "board update" as a deliverable type?
   - How does it handle the "monthly" schedule?

4. **Provide context** - When prompted, share:
   ```
   I'm the CEO of PayFlow, a fintech startup. We just closed our Series A.
   My lead investor Marcus Webb at Sequoia prefers data-driven updates with
   clear asks if we need anything. The board meets quarterly but they want
   monthly async updates in between.
   ```

   **Observe**:
   - Does TP acknowledge this context?
   - Does it offer to save this as memory/context?
   - Watch for a "Setup Confirmation" modal - does it appear?

5. **Review the Setup Confirmation modal** (if it appears):
   - Is the deliverable type correct?
   - Is the schedule what you expected?
   - Is the context/recipient info captured?
   - Click through to confirm or edit

---

### Phase 3: First Generation (3-5 min)

6. **Trigger a run** - Either:
   - Click "Run Now" on the deliverable detail page, OR
   - Ask TP: `Can you generate the first board update now?`

   **Observe**:
   - Is there loading/progress indication?
   - How long does generation take?
   - Where do you end up after generation?

7. **Review the staged output**:
   - Navigate to the review surface (should happen automatically or via attention badge)
   - Read the generated content:
     - Does it match the "board update" format?
     - Does it incorporate your context (PayFlow, Marcus, Series A)?
     - Is the tone appropriate?

---

### Phase 4: Feedback Loop (3-5 min)

8. **Make edits** - The first draft probably isn't perfect. Edit it:
   - Change some wording
   - Add a section
   - Remove something unnecessary

   **Observe**:
   - Is the editor easy to use?
   - Can you see your changes?

9. **Approve with feedback** - Click approve and optionally add a note:
   ```
   Good structure but needs more specific metrics. Also prefer "team" over "we" language.
   ```

   **Observe**:
   - Is there confirmation of approval?
   - Where do you end up after approval?
   - Can you easily get back to the deliverable?

---

### Phase 5: Second Generation (3-5 min)

10. **Run again** - Generate another version:
    ```
    Generate another board update - pretend it's a month later
    ```

    **Observe**:
    - Does the new version incorporate your feedback?
    - Is it noticeably different/better?
    - Check the "Learned Preferences" section on the detail page

11. **Check version history**:
    - Can you see both versions?
    - Can you click to view the previous version?
    - Is the quality trend showing?

---

### Phase 6: Dashboard & Navigation (2-3 min)

12. **Return to dashboard** - Click back or navigate home:
    - Is your new deliverable visible?
    - Does it show the next scheduled run?
    - Is the status (active/paused) clear?

13. **Test the "Latest Output" preview**:
    - On the deliverable detail page, is there an output preview?
    - Can you click through to the full version?

---

### Phase 7: Edge Cases & Stress Tests (3-5 min)

14. **Try ambiguous requests**:
    ```
    Can you make me a thing for my boss?
    ```
    - Does TP ask for clarification?
    - Does it handle vagueness gracefully?

15. **Try conflicting instructions**:
    ```
    Actually make it weekly instead. No wait, biweekly. And change the recipient to my manager, not the board.
    ```
    - Does TP handle changes mid-conversation?
    - Does it confirm the final configuration?

16. **Try to break it**:
    - Refresh the page mid-generation
    - Navigate away during a run
    - Submit an empty message
    - Try very long input

---

## What to Document

### For Each Phase, Note:

1. **What worked well?**
   - Intuitive flows
   - Helpful responses
   - Clear feedback

2. **What was confusing?**
   - Unclear UI elements
   - Unexpected behavior
   - Missing information

3. **What was broken?**
   - Errors
   - Failed actions
   - Lost state

4. **Qualitative feel**:
   - Did it feel fast or slow?
   - Was TP helpful or annoying?
   - Would you trust this for real work?

### Specific Questions to Answer:

| Area | Question |
|------|----------|
| **Onboarding** | Did you understand the app's purpose within 30 seconds? |
| **TP Conversation** | Did TP feel like a helpful assistant or a form wizard? |
| **Context Handling** | Did TP remember and use the context you provided? |
| **Setup Modal** | Was the confirmation step useful or redundant? |
| **Generation** | Was the output quality acceptable for a first draft? |
| **Review Flow** | Was editing and approving intuitive? |
| **Feedback Loop** | Did the second generation improve based on your edits? |
| **Navigation** | Could you always find your way back to where you started? |
| **Visual Design** | Did the UI feel polished or rough? |
| **Trust** | Would you use this for actual work deliverables? |

---

## Bug Report Template

```markdown
### Bug: [Short description]

**Steps to reproduce:**
1.
2.
3.

**Expected:**

**Actual:**

**Screenshot:** [if applicable]

**Severity:** Critical / Major / Minor / Cosmetic
```

---

## Feature Gap Template

```markdown
### Gap: [What's missing]

**User need:** What were you trying to do?

**Current behavior:** What happens now?

**Suggested improvement:** How should it work?

**Priority:** Must-have / Nice-to-have / Future
```

---

## End of Test Checklist

- [ ] Created at least one deliverable
- [ ] Generated at least two versions
- [ ] Made edits and approved at least once
- [ ] Viewed version history
- [ ] Returned to dashboard and found deliverable
- [ ] Tested TP with ambiguous/edge-case requests
- [ ] Documented at least 3 observations (good or bad)

---

## Notes Space

Use this area to capture observations as you test:

```
Phase 1 Notes:


Phase 2 Notes:


Phase 3 Notes:


Phase 4 Notes:


Phase 5 Notes:


Phase 6 Notes:


Phase 7 Notes:


Overall Impressions:


Top 3 Issues:
1.
2.
3.

Top 3 Wins:
1.
2.
3.
```
