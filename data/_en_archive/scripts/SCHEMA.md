# Script JSON Schema — AI Tools Daily

> **Updated 2026-06-02 (iter 16 — pivot EN niche)** — Migrated from "Tài Chính 5 Phút" VN to "AI Tools Daily" EN.
> Channel: `@aitoolsdaily` (handle planned, user to create)
> Niche: Daily AI tool reviews + comparisons + workflow tests
> Audience: developers, content creators, office workers (EN, global, 25-40)
> Previous schema for VN finance: `data/_vn_archive/`

---

## 1. SCHEMA standard JSON

```json
{
  "idea_id": <int>,
  "title": "<60-80 chars, includes #shorts + 1-2 specific hashtags>",
  "hook": "<30-70 chars, first-person test claim or specific outcome>",
  "description": "<200-300 words: hook line + story expand + value teaser + CTA + 8-12 hashtags>",
  "tags": ["<12-20 tags mix brand + tool name + topic + viral>"],
  "scenes": [
    {"voiceover": "<EN sentence, no abbreviations, specific numbers>", "visual_keyword": "<EN 3-5 words universal>", "visual_style": "ai|stock", "visual_prompt": "<EN detailed AI prompt>"},
    ...8 elements
  ]
}
```

---

## 2. CONTENT RULES (locked)

### 2.1 NICHE: AI tools daily review

**5 content pillars:**
| Pillar | % | Format example |
|---|---|---|
| Tool review (single tool) | 35% | "I Tested [Tool] for 7 Days" |
| Comparison head-to-head | 25% | "Claude vs ChatGPT vs Gemini for X" |
| Replace paid stack | 20% | "Free AI Replaced My $200 Subscription" |
| Workflow / automation | 15% | "AI Did [Task] in [Time]" |
| Hidden trick / tip | 5% | "Most Devs Don't Know This [Tool] Hack" |

**KEEP content:**
- AI tools generic (LLMs, image gen, code editors, productivity)
- Workflow automations (Zapier, n8n, custom scripts)
- Free alternatives to paid SaaS
- Honest benchmarks with numbers

**AVOID content:**
- Crypto/Web3 trading (YMYL strict, demonetize risk)
- Health/medical AI (YMYL strict)
- Misleading "AI guaranteed income" claims
- Affiliate-only without testing

### 2.2 TONE: first-person test + numbers

- **First-person "I tested" / "I used" / "I replaced"** — builds trust despite AI voice
- **Specific numbers** — "saved 18 hours", "73% accuracy", "$200/month → $0"
- **Direct, no hype** — avoid "amazing/incredible/insane" unless backed by demo
- **Show the failure too** — "AI got 2 emails wrong" / "Cursor failed after 200k tokens"

### 2.3 ENGLISH WRITING RULES

- **No contractions** in voiceover (TTS pronounces awkwardly): "I do not" not "I don't" — EXCEPT common ones: "I'm", "it's", "you're" OK
- **Spell out numbers under 10**, use digits 10+: "three tools", "47 minutes"
- **Spell out dollar amounts**: "180 dollars" not "$180" (TTS reads "$" as "dollar sign")
- **Acronym handling**: spell out first use: "Large Language Model (LLM)", then LLM OK
- **No `<` `>`**: YouTube API rejects 400 invalidDescription. Pipeline auto-sanitizes `<` → `‹`, `>` → `›`

### 2.4 HOOK MUST MATCH scene 1 voice start (locked from VN pipeline)

**CRITICAL:** `hook` field MUST appear VERBATIM at start of `scenes[0].voiceover`.

Reason: pipeline skip logic deduplicates hook visual + caption. Mismatch → 2 different texts shown simultaneously = repetition feeling.

✅ GOOD:
```json
{
  "hook": "I gave Cursor AI my entire codebase for 7 days. Result: 18 hours saved.",
  "scenes": [
    {"voiceover": "I gave Cursor AI my entire codebase for 7 days. Result: 18 hours saved. I'm a senior dev, average task time dropped from 45 to 12 minutes.", ...}
  ]
}
```

### 2.5 8-SCENE STRUCTURE (45-55s total)

| Scene | Duration | Purpose |
|---|---|---|
| 1 HOOK | 6-10s | Hook claim + specific result number |
| 2 PAIN | 5-7s | Viewer's relatable problem |
| 3 SOLUTION REVEAL | 5-7s | Name the AI tool + key feature |
| 4 DEMO #1 | 8-10s | Specific example with numbers |
| 5 DEMO #2 / Counter | 5-10s | Limitation, edge case, or comparison |
| 6 VERDICT | 5-7s | Final recommendation + when to skip |
| 7 CTA | 3-4s | Comment-bait question |
| 8 SUBSCRIBE | 3-4s | Value prop + brand consistency |

---

## 3. VISUAL RULES (locked from VN pipeline)

### 3.1 Caption (karaoke sub)
- Font: BeVietnamPro-ExtraBold (works for EN too — clean sans-serif)
- Fontsize 110, white, stroke black 3, shadow offset y+7
- Position y=1280, max_words=3 per chunk
- Sync via Google TTS SSML timepoints (en-US Wavenet)

### 3.2 Hook visual
- Font: Montserrat-ExtraBold, white + bg semi-black pill 0.65
- Fontsize dynamic 82-125, position y=700, duration 2.5s

### 3.3 Visual style per scene
- **Scenes 1-6 (content):** `visual_style="ai"` Pollinations Flux with detailed dev/dashboard prompts
- **Scene 7 (comment CTA):** `visual_style="stock"` keyword "hands typing message phone screen close up"
- **Scene 8 (subscribe CTA):** `visual_style="ai"` prompt "Young tech professional smiling pointing up at subscribe button, modern office, photorealistic cinematic"

### 3.4 AI prompts for EN niche
EN-specific concepts:
- "Modern AI dashboard UI minimal dark theme"
- "Developer workstation multiple monitors code editor"
- "Stressed developer office laptop late night sticky notes"
- "Modern SaaS landing page mockup on monitor"
- "Code editor showing test pass green checkmarks"
- "Hand holding credit card next to laptop subscription page"

### 3.5 Ken Burns + 24fps (carried from iter 13, 15)
- Duration 15s (covers max voice scene, no loop)
- Linear zoom `z=1.0+0.15*on/total_frames`
- All clips `c.set_fps(24)` normalize

---

## 4. PIPELINE / ENCODER (carried from VN)

### 4.1 Voice (en-US Wavenet)
3 voices rotation:
- `en-US-Wavenet-D` (Male, confident mature) — daily 1
- `en-US-Wavenet-J` (Male, young energetic) — daily 2
- `en-US-Wavenet-F` (Female, clear professional) — daily 3

SSML `languageCode: "en-US"`, speakingRate 1.15, pitch 0.0, volumeGainDb 2.0.

### 4.2 Upload privacy
- Default: `public` (`os.environ.get("YT_PRIVACY", "public")`)
- Override `YT_PRIVACY=private` for review

### 4.3 Encoder
| Platform | Codec | Preset | FPS | Bitrate |
|---|---|---|---|---|
| Windows local | libx264 | ultrafast | 24 | 5500k |
| Linux CI | libx264 | veryfast | 24 | 5500k |

### 4.4 Cadence
- 1 video/24h (channel < 100 sub)
- Cron `0 23 * * *` UTC = 6 AM Vietnam = 11 PM US Pacific previous day (target US/UK morning commute)

---

## 5. DESCRIPTION FORMAT

```
<Hook line 80-100 chars>

<Body 100-150 words: story expand, specific numbers, value teaser>

🔔 Subscribe @aitoolsdaily — 1 new AI tool tested every day at 8 AM PT.

⚠️ Personal testing, not paid promotion. Tools change pricing/features fast.

#shorts #ai #aitools + 5-8 tool-specific hashtags
```

Pipeline auto-appends:
- Disclaimer (no paid promo, results vary)
- Kevin MacLeod CC-BY music credit
- Business contact email

---

## 6. ANTI-TEMPLATING (rotate to avoid algorithm pattern-detect)

- **Tool rotation** per 5 scripts: 2 LLM (Claude/ChatGPT/Gemini), 1 IDE (Cursor/Windsurf/Cline), 1 image gen (Flux/Krea/Ideogram), 1 workflow (n8n/Zapier/Make)
- **Voice rotation** daily (D/J/F) auto via `datetime.now().day % 3`
- **Pillar rotation** per 5 scripts: at least 3 different pillars
- **Number rotation**: avoid same outcome ("saved X hours") in consecutive videos

---

## 7. SAFETY / COMPLIANCE

- **No paid promotion claim without disclosure** — always note "personal testing"
- **No misleading time/cost saving without test data**
- **Affiliate links require disclosure** in description (FTC requirement)
- **AI-generated voice declaration** — `containsSyntheticMedia: True` in YouTube body (already set)

---

**END OF SCHEMA** — Update on each rule iteration with user.
