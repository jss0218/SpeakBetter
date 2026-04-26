Create a single setup screen for "speakBetter" — a public speaking 
training app. This replaces a two-step flow with one clean page.

VISUAL STYLE:
Background: #FAFAF7 (warm white)
Accent: #E8B84B (yellow)
Text: #1A1A1A
Border radius: 12–16px everywhere
Borders: 0.5px solid #E8E6E0 (no harsh shadows)
Font: clean sans-serif, 500 weight headings, regular body
Tone: warm, encouraging, minimal

---

TOP BAR:
Left: "speakBetter" logo — "speak" in #1A1A1A, 
"Better" in #E8B84B. Small, unobtrusive.
No nav links, no other elements.

---

HERO TEXT (centered, top third of page):
Heading: "Let's get you ready."
Large, bold, centered. #1A1A1A.
Subheading: "Set up your session and start practicing."
Muted gray (#888), centered, regular weight, 
slightly smaller than heading.

---

SECTION 1 — "What are you practicing for?"
Section label: small uppercase muted text, 
left-aligned above cards. Letter-spacing 0.06em.

Two cards side by side, centered on page:

  Card 1: "Presentation"
  Icon: slides/screen icon (simple, outlined)
  Description: "Pitch decks, project updates, 
  stakeholder meetings"

  Card 2: "Pitch"
  Icon: lightbulb icon (simple, outlined)
  Description: "Startup pitches, investor 
  meetings, demos"

Card styles:
- White bg (#FFFFFF)
- Border: 0.5px solid #E8E6E0
- Border radius: 14px
- Padding: 28px 24px
- Icon top, then title bold, then description muted
- Min width: 200px, max width: 240px
- Hover: very subtle shadow lift
- Selected state: 2px solid #E8B84B border, 
  background tint #FFFBEF
- Unselected cards slightly dim (opacity 0.7) 
  when one is selected
- Smooth transition 0.2s ease on all state changes

---

SECTION 2 — "Audience size"
Section label same style as above.

Three pill toggle buttons in a row, centered:
  "Small  1–10"
  "Medium  20–50"  
  "Large  100+"

Pill styles:
- Unselected: white bg, 0.5px border #E8E6E0, 
  text #666, padding 10px 22px, border-radius 99px
- Selected: bg #E8B84B, text #5C3D00, 
  border-color #E8B84B, font-weight 500
- Hover on unselected: border #E8B84B, text #E8B84B
- Transition 0.15s ease

---

SECTION 3 — "Environment"
Section label same style as above.

Three cards in a row, centered:

  Card 1: "Conference room"
  Simple illustration: small rectangular room, 
  oval table, 4–6 seat silhouettes around it.
  Intimate, small scale.

  Card 2: "Classroom"
  Simple illustration: rows of small desks, 
  chalkboard at front. Moderate scale.

  Card 3: "Lecture hall"
  Simple illustration: tiered seating, 
  large stage at bottom. Big scale.

Illustration style: flat, minimal, 2–3 color max.
Use #E8B84B as the accent color in each illustration.
Use #F0EDE6 as the base/room color.

Card styles: same as section 1 cards but slightly 
smaller. Selected state: same yellow border + tint.

---

SECTION 4 — "How long is your session?"
Section label same style as above.

A single clean slider:
- Track: thin (4px), rounded, #E8E6E0 background
- Fill left of thumb: #E8B84B
- Thumb: 18px circle, white with #E8B84B border 2px, 
  subtle shadow
- Range: 1 minute to 15 minutes
- Default: 5 minutes
- Below slider: current value displayed centered
  in format "5 minutes" — updates live as slider moves
  Text: #E8B84B, font-weight 500, font-size 14px

---

SECTION 5 — Optional topic input
No section label — just the input, understated.

Single text input, full width of content area:
Placeholder: "Topic or talking points (optional) 
— e.g. Q3 earnings, climate policy, product launch"
Style: 
- Border: 0.5px solid #E8E6E0
- Border-radius: 10px
- Padding: 12px 16px
- Font-size: 14px
- Focus state: border-color #E8B84B, 
  very light yellow bg tint
- No label above it — placeholder does the work

---

CTA BUTTON:
"Start session →"
Full width of content area (not edge to edge — 
respects content margins).
Background: #E8B84B
Text: #5C3D00, font-weight 500, font-size 15px
Border-radius: 99px (full pill)
Padding: 14px
Disabled state: opacity 0.4, not clickable — 
active only when BOTH a practice type AND 
environment are selected.
Hover: slightly darker yellow (#D4A93C), 
smooth 0.15s transition.
No shadow.

---

LAYOUT RULES:
- All content centered in a max-width container (560px)
- Sections separated by 32px vertical gap
- Page has generous top padding (60px) and 
  bottom padding (40px)
- Mobile responsive: cards stack vertically, 
  pills wrap, slider stays full width

---

COMPONENT STATE SUMMARY:
Track these as internal state:
- practiceType: 'presentation' | 'pitch' | null
- audienceSize: 'small' | 'medium' | 'large' (default: 'medium')
- environment: 'conference' | 'classroom' | 'lecture' | null
- duration: number in minutes (default: 5)
- topic: string (default: '')

Start session button disabled until:
practiceType !== null AND environment !== null

---

FEEL: Warm, focused, encouraging. Like a calm 
coach asking you a few questions before you go on. 
Not a form. Not a dashboard. A conversation 
you can complete in 30 seconds.

Export as a single self-contained React component 
with all state managed internally via useState.
Named: SetupScreen