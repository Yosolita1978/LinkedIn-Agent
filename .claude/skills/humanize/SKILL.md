---
name: humanize
description: Polish a LinkedIn draft so it sounds like Cristina, strip AI patterns, and list what changed
allowed-tools:
  - Read
  - Edit
  - Glob
  - Grep
argument-hint: "[draft file in content/drafts/, or paste the text]"
---

# Humanize

Rewrites a LinkedIn draft so it sounds like Cristina's real posts, not like AI.

## Steps

1. **Find the draft:**
   - A file path: use that file.
   - Pasted text: use the text.
   - No argument: use the newest file in `content/drafts/`.

2. **Read the voice:**
   - `content/voice.md`. The `## LinkedIn` section wins over the rest of the guide.
   - Every file in `content/samples/`. Files starting with `FAVORITE-` are the model posts.

3. **Run the mechanical checks** and note every hit:
   - Em dashes (`—`). Replace with a colon, comma, or period.
   - Emojis in the body (emojis inside a tagged person's name are fine).
   - Lines starting with `-`, `•`, `*`, or `1.`. Turn them into narrated sentences.
   - Banned phrases from `voice.md`: "delve", "dive in", "unpack", "landscape", "leverage", "foster".
   - Other common AI giveaways: "game-changer", "in today's fast-paced", "I'm thrilled to announce", "excited to share", "navigate", "journey", "testament", "elevate", "seamless", "robust", "unlock", "harness".
   - The "not X, not Y, Z" rhythm, and "It's not about X, it's about Y".
   - "You should" or any "you" that lectures.
   - Hashtags: 3 to 7, at the end only.

4. **Run the voice checks** by comparing the draft to the samples:
   - Does the hook go straight into the moment or a blunt statement? No warm-up line.
   - Is emotion shown through a specific detail instead of named ("I felt inspired")?
   - Is there a moral or a lesson being taught? Turn it into an intention or a reflection.
   - Does the sentence rhythm vary? Mix short impact lines with longer ones.
   - Are there stiff transitions ("Additionally", "Furthermore", "In conclusion")? Remove them.
   - Is it longer than it needs to be? Cut.
   - Would a light touch of the full voice fit naturally (a parenthesis aside, one Spanish word)? Only add it if it isn't forced.

5. **Rewrite the post.** Keep every fact, name, link, and the main story exactly as they are. Never add new facts.

6. **Save it.** If the draft was a file, update the post in place, keep the header, and set `status: ready`.

7. **Show the result:**
   - The rewritten post inside a code block so it is easy to copy.
   - Then a short **Changes** list (5 to 8 lines max) with what was fixed and why, e.g. `"I'm excited to share" → straight into the moment (warm-up line)`.
