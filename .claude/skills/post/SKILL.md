---
name: post
description: Draft a LinkedIn post in Cristina's voice from a pillar or idea, and save it to content/drafts/
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
argument-hint: "[pillar or idea, e.g. \"agentic-ai\" or \"what I learned at the n8n event\"]"
---

# Post

Drafts one LinkedIn post in Cristina's voice and saves it to `content/drafts/`.

## Steps

1. **Read the source files** (all paths from the repo root):
   - `content/voice.md`. The `## LinkedIn` section wins over the rest of the guide.
   - `content/audience.md`
   - `content/pillars.md`
   - `content/hooks.md`
   - Every file in `content/samples/`. Files starting with `FAVORITE-` are the model posts.
   - `content/ideas.md`
   - Every file in `content/published/`. These are final versions; the comment at the bottom of each one lists what Cristina changed from the draft. Apply those lessons.

2. **Work out the topic** from the argument:
   - A pillar name: pick the oldest idea with status `new` for that pillar in `ideas.md`. If there is none, ask what the post is about.
   - An idea or sentence: use it as the topic and match it to a pillar.
   - No argument: show up to 3 `new` ideas from `ideas.md` and ask which one, or ask for a topic.

3. **Get the real story.** The voice depends on real moments, so never invent facts, names, numbers, dates, events, or quotes. If the topic doesn't already include them, ask up to 3 short questions in one message, for example:
   - What actually happened? (the moment, a detail, what surprised you)
   - Who should be thanked or tagged?

4. **Pick a template** from `content/templates/` that fits the topic. Say which one in one line.

5. **Offer 3 hooks** using the formulas in `content/hooks.md`, each from a different formula. Wait for Cristina to pick one, rewrite one, or ask for more.

6. **Write the post** following the template and the voice. Before showing it, check it against every rule in "Still banned on LinkedIn" in `voice.md`. In particular:
   - No em dashes (`—`). Use a colon, comma, or period.
   - No emojis in the body.
   - No bullet or numbered lists. Narrate them.
   - No "not X, not Y, Z" rhythm.
   - "You" only to invite or include, never to lecture.
   - 3 to 7 hashtags at the end.

   Keep it short and tight (this is how Cristina edits drafts in `content/published/`):
   - Put the hook and its contradiction in one paragraph, not split across lines.
   - One idea per paragraph. Cut any line that only repeats the point ("Two very different rooms.").
   - Thank the hosts and organizers by name. Thank everyone else as a group ("every speaker who shared their work"), never as a long list of names.
   - No link unless Cristina asks for one.
   - Don't explain step by step how something works. If there's an image or a link, let it carry the details.
   - Cut catchy lines that only restate the point, and closing slogans or taglines that repeat the hook.
   - Soften absolute claims about technical facts ("can't spell" becomes "can't spell correctly 100% of the time").
   - On technical or promo posts, use plain English ("In short:") instead of "Léase:".
   - Promo posts: end with a call to action before the link ("Register for the whole event here:"), and use the full official names of organizations.
   - Stop when the story is told.

7. **Save the draft** to `content/drafts/YYYY-MM-DD-short-slug.md` (today's date), with this header followed by the post:

   ```
   ---
   pillar:
   template:
   status: draft
   posted_on:
   link:
   ---
   ```

8. **Mark the idea as used.** If the topic came from `ideas.md`, change its status to `drafted`.

9. **Show the result**: the post inside a code block so it is easy to copy, then one line with the file path. Nothing else around it.

Suggest `/humanize` on the draft as the next step.
