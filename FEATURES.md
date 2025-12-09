# Features We Can Add

A collection of feature ideas to make Reading Buddy more useful.

---

## High-Value Features

### 1. Reading Progress Tracking & Notes
**Why:** Currently you can only mark items as "read" or "unread". Adding progress tracking would help with longer content.

**What to add:**
- Progress states: `unread → in_progress → read`
- Personal notes/takeaways when marking complete
- A `/wip` command to see what you're currently reading

**Benefit:** Knowing what you started but didn't finish prevents the "I'll get to it" pile from growing silently.

---

### 2. Weekly Summary & Insights
**Why:** We have daily digests but no reflection mechanism.

**What to add:**
- Scheduled weekly message (e.g., Sunday evening) with:
  - Items read this week
  - Average time items sat unread
  - Tag trends (reading more AI vs. security lately?)
  - Oldest unread item ("this has been waiting 23 days...")

**Benefit:** Gamifies your learning habit and creates accountability without being annoying.

---

### 3. Content Prioritization System
**Why:** Not all saved items are equal. Some are "watch when bored" vs. "need for work".

**What to add:**
- Priority levels: `low`, `medium`, `high`, `urgent`
- `/focus` command that shows only high/urgent items
- Let Gemi prompt you about priority when adding ("this looks work-related, is it urgent?")

**Benefit:** Morning digest could prioritize what actually matters instead of just "unread".

---

### 4. Estimated Read/Watch Time
**Why:** You might have 5 minutes or 45 minutes - knowing what fits helps.

**What to add:**
- Auto-estimate time based on content type (articles ~5-15min, videos check duration, etc.)
- Filter by time available: "what can I read in 10 minutes?"
- Store actual time spent when marking complete (optional)

**Benefit:** Removes decision fatigue. "I have 10 min" → instant suggestion.

---

## Learning Enhancement Features

### 5. Spaced Repetition for Key Learnings
**Why:** Reading without retention is just entertainment.

**What to add:**
- When marking read, optionally add 1-2 key takeaways
- Gemi randomly quizzes you on old learnings ("remember that video about RAG? what was the main insight?")
- Track which learnings you remember vs. forget

**Benefit:** Transforms passive consumption into active learning.

---

### 6. Topic-Based Learning Paths
**Why:** Collecting scattered content lacks direction. Paths create structure.

**What to add:**
- Group items into themes: "Learning Rust", "Security Deep Dives"
- Track completion percentage per path
- `/paths` command to see your learning journeys

**Benefit:** Gives structure to self-directed learning instead of random consumption.

---

## Quality of Life Improvements

### 7. "Not Interested Anymore" Option
**Why:** Some saved items become irrelevant. Currently no way to dismiss without reading.

**What to add:**
- `archived` status distinct from `read`
- `/cleanup` command to review old items and archive stale ones
- Let Gemi occasionally ask "still interested in this 30-day-old item?"

**Benefit:** Keeps your list fresh and reduces guilt about unread items.

---

### 8. Reading Mood/Context Matching
**Why:** What you want to read depends on your state - tired vs. energized, work mode vs. relaxing.

**What to add:**
- Content mood tags: `deep-focus`, `light`, `entertainment`, `practical`
- Commands like `/light` or `/deep` to match your current energy
- Time-aware suggestions (heavy content in morning, light in evening)

**Benefit:** Stops you from opening a dense paper when you really wanted something casual.

---

### 9. Source Tracking & Curation
**Why:** Some sources consistently give you good content; others waste your time.

**What to add:**
- Track source/domain of links
- `/sources` shows which sources you read most from
- Mark sources as "always interesting" or "usually skip"

**Benefit:** Helps curate your information diet over time.

---

### 10. Integration with Existing Habits
**Why:** Water reminders already exist. Bundle habits together.

**What to add:**
- Morning message asks "what will you read today?" (commitment)
- Evening reflection "did you read what you planned?"
- Pomodoro-style: "you've been working for a while, read something for 5 min?"

**Benefit:** Habit stacking is more effective than isolated reminders.

---

## Quick Wins

| Feature | Effort | Impact |
|---------|--------|--------|
| `/random` - pick a random unread item | Low | Fun way to break decision paralysis |
| `/oldest` - show your oldest unread items | Low | Guilt-driven motivation |
| `/today` - what did I add/read today | Low | Quick daily review |
| Share reading list export | Medium | Backup or share with friends |
| Content type stats (videos vs articles) | Low | Understand consumption habits |

---

## Priority Recommendations

Based on current usage patterns, these three would add the most value:

1. **Weekly Summary (#2)** - Adds reflection mechanism without more daily effort
2. **Estimated Read Time (#4)** - Practical, removes friction when deciding what to consume
3. **Not Interested Anymore (#7)** - Prevents list bloat which kills motivation over time
