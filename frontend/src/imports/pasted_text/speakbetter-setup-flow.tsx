Create a setup flow screen for "speakBetter" — a public speaking 
training app. This appears after the user clicks "Get started" 
on the landing page.

VISUAL STYLE:
Background: #FAFAF7 (warm white)
Accent: #E8B84B (yellow)
Text: #1A1A1A
Border radius: 12–16px everywhere
Borders: 0.5px solid #E8E6E0
Font: clean sans-serif, 500 weight headings, regular body
Tone: warm, conversational, encouraging — like a coach 
asking you questions, not a form to fill out.

---

LAYOUT:
Full page, vertically scrollable.
Single centered content column, max-width 520px, 
auto horizontal margins.
Top padding: 48px. Bottom padding: 80px.
Each question block separated by 40px vertical gap.
Questions appear as a continuous scroll — 
no pagination, no steps, no progress bar.

---

TOP:
Small "speakBetter" wordmark top-left.
"speak" in #1A1A1A, "Better" in #E8B84B.
No other nav elements.

---

PAGE HEADING (top of scroll area):
"A few quick questions."
Large, bold, #1A1A1A, centered.
Subtext below: "We'll tailor your session to match."
Muted #888, centered, regular weight.
32px gap below before first question.

---

QUESTION 1 — "What are you practicing for?"
Question text: 18px, font-weight 500, #1A1A1A
Small muted subtext below question: 
"We'll shape your Q&A around this."
14px, #999, regular weight.
24px gap between question text and options.

Three selectable cards in a row:

  Card 1: "Investor Pitch"
  Icon: simple money/chart icon
  Subtext: "Convince a room to believe in your idea"

  Card 2: "Presentation"
  Icon: simple slides icon
  Subtext: "Inform, update, or walk through a topic"

  Card 3: "Interview"
  Icon: simple person/chat icon
  Subtext: "Practice answering under pressure"

Card styles:
- White bg, 0.5px border #E8E6E0, 14px radius
- Padding: 20px 16px
- Icon top (24px, #E8B84B tint), title bold 14px, 
  subtext muted 12px
- Selected: 2px border #E8B84B, bg #FFFBEF
- Unselected when one chosen: opacity 0.6
- Hover: subtle border color shift to #E8B84B
- Transition: all 0.2s ease

---

QUESTION 2 — "How many people are you talking to?"
Question text same style as Q1.
Subtext: "This sets your audience size."

A large number input with +/- controls:

Layout: [ − ]  [ 12 ]  [ + ]
- Center number display: 48px font, font-weight 500, 
  #1A1A1A, min-width 80px, text centered
- Minus and Plus buttons: 40px circles, 
  border 0.5px #E8E6E0, bg white, 
  #666 icon color, font-size 20px
- Plus/minus hover: border #E8B84B, color #E8B84B
- Range: 1 to 100
- Default: 12
- Below the control, a subtle label updates live:
  1–10: "Small audience — intimate setting"
  11–30: "Medium audience — conference room"  
  31–100: "Large audience — lecture hall"
  Label style: 13px, #999, centered, italic

  This label also determines the grid layout used 
  in the live session (6 cells / 9 cells / 12 cells)

---

QUESTION 3 — "How long do you have?"
Question text same style as Q1.
Subtext: "We'll count you down and prompt Q&A when time's up."

Slider component:
- Track: 4px height, rounded, #E8E6E0 background
- Fill left of thumb: #E8B84B
- Thumb: 20px circle, white bg, 2px border #E8B84B
- Range: 1 to 20 minutes
- Default: 5
- Snap to whole minutes only
- Live label below slider, centered:
  Format: "5 minutes"
  Style: #E8B84B, font-weight 500, 16px
  Updates live as thumb moves.

---

QUESTION 4 — "Engagement feedback style"
Question text same style as Q1.
Subtext below question (two lines, muted #999 14px):
"By default, engagement shows through your audience's 
facial expressions — just like a real room."
Second line: "Turn this on if you'd like a visual 
color indicator as well."

Toggle switch + label layout:
Left side: toggle switch component
  - Off state: track #E0DDD6, thumb white
  - On state: track #E8B84B, thumb white
  - Smooth sliding transition 0.2s ease
  - 44px wide × 24px tall

Right side of toggle, two lines of text:
  Line 1: "Color engagement rings" — 14px, 
  font-weight 500, #1A1A1A
  Line 2 (muted, 12px, #999):
  "Audience frames glow green → yellow → red 
  based on how engaged they are."

When toggle is OFF:
  Below toggle area, a small example row appears:
  3 tiny mock zoom cells (just rounded rectangles, 
  40×30px each) showing faces with natural expressions.
  Label below: "Reactions shown through expressions"
  Style: 11px, #bbb, centered

When toggle is ON:
  Same 3 tiny mock zoom cells but now each has 
  a colored border:
  Left cell: 2px border #4CAF50 (green)
  Middle cell: 2px border #E8B84B (yellow)  
  Right cell: 2px border #F44336 (red)
  Label below: "Reactions shown through expressions + color"
  Style: 11px, #bbb, centered

  Animate the swap between these two preview 
  states with a 0.3s fade.

---

CTA BUTTON — "Start session →"
Sticky to bottom of viewport — stays visible 
as user scrolls.
Full width of content column (520px max).
Background: #E8B84B
Text: #5C3D00, font-weight 500, 15px
Border-radius: 99px
Padding: 14px
Disabled: opacity 0.4, cursor not-allowed
Active when: practiceType is selected AND 
audienceCount > 0 AND duration > 0.

Sticky container:
- Position: fixed, bottom: 0
- Full width, centered
- Background: linear-gradient(transparent, #FAFAF7 40%)
  so it fades in from the page bg
- Padding: 16px 0 24px
- The gradient masks the scroll content 
  disappearing behind the button naturally

---

COMPONENT STATE:
Track internally via useState:

practiceType: 'pitch' | 'presentation' | 'interview' | null
audienceCount: number (default: 12)
duration: number in minutes (default: 5)
colorEngagement: boolean (default: false)

On "Start session" click, call onStart prop with:
{
  practiceType,
  audienceCount,
  duration,
  colorEngagement
}

---

ACCESSIBILITY NOTE on color engagement toggle:
The toggle description should never use the word 
"autism" or any diagnostic framing. 
Keep it purely functional:
"Prefer explicit color cues over subtle expressions? 
Turn this on."
Clean, neutral, no assumptions about the user.

---

FEEL: Conversational. Like filling out a 
thoughtful questionnaire, not a settings panel. 
Each question breathes. Nothing feels cramped. 
The sticky button always reminds them 
they're one tap from starting.

Export as single self-contained React component.
Named: SetupFlow
Props: onStart: (config: SessionConfig) => void