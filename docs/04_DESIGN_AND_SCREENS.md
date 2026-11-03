# Design system and screen map

Approved latest direction is light Warm Editorial Terracotta: background approximately #FDFCF9, white surfaces, subtle warm-gray borders #EAE6DF, dark charcoal body #292929, deep espresso serif headlines, clear sans-serif body and controls, primary terracotta approximately #B74720, neutral low-contrast shadows. Approximate colors from visual concepts must be validated in implementation, particularly text contrast. Not heavy orange / monochromatic blue / dark mode. High-quality raised cards, buttons and disciplined whitespace without excessive decoration. Professional engineering intelligence, not general news.

Generated boards are raster concepts, not editable Figma documents. `01_engineering_onboarding.png` and `02_technical_briefings.png` override older designs: do not use older consumer-news headlines or heavily tinted backgrounds. Mock image logos, typography, dates and illustrations are visual placeholders; check intellectual-property usage and provide user-owned/licensed assets before launch. No assumption that raster board elements can be imported as editable components.

## Required screen map
1. Welcome/roles, multi-select, skip.
2. Select technical focus areas, search, skip.
3. Follow specific stack with searchable categories, select/skip.
4. Signal preferences and opt-in push, open feed.
5. Four separate cards states: Feed, Your Stack (with why), Trending, AI.
6. Same feed in List, selected item/position retained.
7. Topic filter, search, Explore topics and search results.
8. Your Stack empty state and manage/follow/optionally versions.
9. Saved list and empty state; share and source actions.
10. Settings, interest/stack edit, notification and accessible reading preferences.
11. Caught up, no network/error/retry, loading, no search results, corrections/withdrawals, long text and permission denial.

Each card: category/update type, useful title, compact explanatory summary, evidence-qualified relevance and next action, source/updated time, original link, save/share, accessible navigation. Show exactly Feed · Your Stack · Trending · AI. Horizontal space and text sizing tested on small devices; alternate top scrolling or minimum targets if needed. Reserve vertical navigation gestures and explicit Cards/List. Preserve four-segment onboarding progress; generated boards sometimes misrender controls and should not be treated as normative behavior.

## Content and asset guidance
Use real/licensed or neutral subject-specific illustrations; random AI chips are not mandatory. App needs accessible alt text, image fallback and no dependence on images for essential content. Give article text space to grow/scroll for accessibility; a card is a reading unit, not a strict fixed-height clipping constraint. Buttons and tap targets meet platform accessibility standards, contrast verified programmatically and visually, talkback/voiceover labels, reduced motion.
