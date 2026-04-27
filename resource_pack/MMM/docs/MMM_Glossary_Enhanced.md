# BTMM (Beat The Market Maker) Glossary - Enhanced for Strategy Identification

**Purpose**: This glossary helps identify key MMM strategy terms when developing strategies and uploading to the strategy database. Terms are mapped to chart patterns and strategy types used in the system.

**Last Updated**: 2025-01-22

---

## Chart Pattern Terms (Mapped to Database Chart Patterns)

### 22 Trade → `22_trade`
**Definition**: A specific MMM-style setup with two legs in one direction, then two in the opposite direction (2-up, 2-down or vice versa). Often occurs at key levels or during specific sessions.

**Strategy Context**: 
- Look for "22 trade", "two-two trade", or "2-2 trade" in strategy descriptions
- Typically involves counting swings or legs
- Often combined with session timing (London, NYC)
- May reference I-HOD/I-LOD or market maker spread

**Related Terms**: Counting levels, session opens, blue box zones

---

### Stop Hunt / Trap Move → `stop_hunt`
**Definition**: An aggressive move by the market maker to trigger stops of retail traders. Price briefly sweeps obvious stops beyond a level then reverses. Used to identify false breakouts and trap liquidity before the real move.

**Variations**:
- **Extended stop hunt**: Price extended beyond normal 25-50 pip stop hunt; occurs when traders refuse to commit funds
- **M top**: A type of stop hunt used to trap traders and validate retail orders (appears at HOD)
- **W bottom**: A type of stop hunt used to trap traders and validate retail orders (appears at LOD)
- **V top**: A type of stop hunt that does not present a second leg (forms the HOD)
- **V bottom**: A type of stop hunt that does not present a second leg (forms the LOD)

**Strategy Context**:
- Look for "stop hunt", "trap move", "stop sweep", "liquidity grab"
- Often occurs at obvious support/resistance levels
- May reference "shift bar" or "candle spike"
- Typically followed by reversal in opposite direction

**Related Terms**: M top, W bottom, V top, V bottom, shift bar, candle spike, extended stop hunt

---

### M/W Reversal → `m_w_reversal`
**Definition**: M (double top) or W (double bottom) formation. Two peaks or troughs suggesting reversal. Often above/below key zones (e.g. blue box).

**Variations**:
- **M top**: Double top formation at HOD (high of day)
- **W bottom**: Double bottom formation at LOD (low of day)

**Strategy Context**:
- Look for "M formation", "W formation", "double top", "double bottom"
- Often appears at HOD or LOD
- May be part of stop hunt pattern
- Used to validate retail orders

**Related Terms**: Stop hunt, HOD, LOD, blue box, peak formation

---

### Counting Levels → `counting_levels`
**Definition**: Identifying and numbering significant highs/lows or swings (e.g. 1–2–3, 5-wave) to define structure and potential reversal or continuation points.

**Strategy Context**:
- Look for "counting levels", "swing counting", "leg counting", "wave counting"
- Often used with 22 trade pattern
- Helps identify structure and potential reversal points
- May reference numbered swings or legs

**Related Terms**: 22 trade, structure, swings, legs

---

### Blue Box / Key Zone → `blue_box`
**Definition**: Defined key zone (e.g. high-low range, session open, specific level) where setups are taken. MMM-style trading zone.

**Strategy Context**:
- Look for "blue box", "trading zone", "key zone", "strike zone"
- Trading zone: Area where it's safe to enter a trade (needs to be within 15-20 pips off HOD and LOD)
- Often combined with session opens or I-HOD/I-LOD

**Related Terms**: Trading zone, I-HOD, I-LOD, session open, HOD, LOD

---

### Straightaway → `straightaway`
**Definition**: A trade used by the market maker to create margin calls and damage trader accounts. Sustained directional move with little pullback.

**Strategy Context**:
- Look for "straight away", "straightaway", "one-way move"
- Typically traded in the direction of the move or on first meaningful pullback
- May reference margin calls or account damage

**Related Terms**: Vector, trend, market maker trend

---

## Session & Timing Terms

### Session Open / Kill Zone → `session_open`
**Definition**: Setup around fixed-time session opens (e.g. London, NY) or designated 'kill zones'. The time dealers are active in their respective market (approximately 6 hours in duration).

**Sessions**:
- **Asian Session**: Sets I-HOD and I-LOD
- **London Session**: Major trading session, often where key moves occur
- **NYC Session**: Major trading session, often where key moves occur
- **Gap Time**: Changeover between sessions where one market maker transfers instructions to the oncoming dealer

**Strategy Context**:
- Look for "London session", "NYC session", "session open", "kill zone", "gap time"
- Often combined with 22 trade or stop hunt patterns
- May reference specific times (e.g., 8:00 AM London, 8:00 AM NYC)

**Related Terms**: Gap time, London session, NYC session, time mapping

---

## Level & Structure Terms

### I-HOD (Initial High of Day)
**Definition**: The high of the day set during Asian market hours.

**Strategy Context**:
- Used to define market maker spread (distance between I-HOD and I-LOD)
- Less than 50 pips is ideal for market maker spread
- Often used as reference for trading zones and setups

**Related Terms**: I-LOD, HOD, market maker spread, trading zone

---

### I-LOD (Initial Low of Day)
**Definition**: The low of the day set during Asian market hours.

**Strategy Context**:
- Used to define market maker spread (distance between I-HOD and I-LOD)
- Less than 50 pips is ideal for market maker spread
- Often used as reference for trading zones and setups

**Related Terms**: I-HOD, LOD, market maker spread, trading zone

---

### HOD (High of Day)
**Definition**: The highest point on a chart in a 24-hour period.

**Strategy Context**:
- M tops often appear at HOD
- Trading zones should be within 15-20 pips of HOD
- Used with high/low board tracking

**Related Terms**: LOD, I-HOD, peak formation, M top

---

### LOD (Low of Day)
**Definition**: The lowest point on a chart in a 24-hour period.

**Strategy Context**:
- W bottoms often appear at LOD
- Trading zones should be within 15-20 pips of LOD
- Used with high/low board tracking

**Related Terms**: HOD, I-LOD, W bottom, V bottom

---

### Market Maker Spread
**Definition**: The distance between the I-HOD and the I-LOD. Less than 50 pips is ideal.

**Strategy Context**:
- Used to identify favorable trading conditions
- Narrow spread suggests consolidation/position building
- Wide spread may indicate volatility or extended moves

**Related Terms**: I-HOD, I-LOD, consolidation, market maker trend

---

### Peak Formation
**Definition**: The highest point on the chart. Can occur intraday and intra-week.

**Strategy Context**:
- May indicate reversal points
- Used with M top patterns
- Related to HOD tracking

**Related Terms**: HOD, M top, reversal

---

## Trend & Movement Terms

### Market Maker Trend
**Definition**: The real trend of the market, different from what retail traders see and perceive.

**Strategy Context**:
- Look for "market maker trend", "real trend", "true trend"
- May differ from apparent retail trend
- Used to identify actual market direction

**Related Terms**: Trend, reset, market sentiment

---

### Trend / Reset
**Definition**: 
- **Trend**: Slow, steady movement of price in a unidirectional swing until targets are achieved
- **Reset (Trend Reset)**: Market maker makes a pullback to book profit but needs to continue with current trend direction to achieve larger goal

**Strategy Context**:
- Look for "trend reset", "reset", "pullback"
- Resets are opportunities to enter in trend direction
- Used to identify continuation vs reversal

**Related Terms**: Market maker trend, correction, rise

---

### Correction
**Definition**: The lowering of price (in context of uptrend).

**Strategy Context**:
- Part of trend reset pattern
- Opportunity to enter in trend direction
- Different from reversal

**Related Terms**: Reset, rise, trend

---

### Rise
**Definition**: The increase in price.

**Strategy Context**:
- Part of trend structure
- Used in counting levels
- May reference swing or leg counting

**Related Terms**: Correction, trend, vector

---

### Vector
**Definition**: A rapid change in price, in any direction. An anomaly on the chart.

**Strategy Context**:
- Look for sudden, rapid price movements
- May indicate stop hunt or straightaway
- Often precedes significant moves

**Related Terms**: Straightaway, stop hunt, candle spike

---

## Consolidation & Position Building Terms

### Consolidation
**Definition**: Any area where price appears to chop. In reality, market makers are building positions.

**Strategy Context**:
- Look for "consolidation", "choppy", "ranging"
- Often precedes significant moves
- Market makers accumulating positions

**Related Terms**: Holding the level, market maker spread

---

### Holding the Level
**Definition**: Price will consolidate in a tight range; used to accumulate contracts.

**Strategy Context**:
- Similar to consolidation
- Indicates position building
- May precede breakout or reversal

**Related Terms**: Consolidation, trading zone

---

## Entry & Exit Terms

### Trading Zone
**Definition**: The area where it is safe to enter a trade. Needs to be within 15-20 pips off of the HOD and LOD.

**Strategy Context**:
- Look for "trading zone", "strike zone", "entry zone"
- Must be within 15-20 pips of HOD/LOD
- Often combined with blue box or key levels

**Related Terms**: Blue box, HOD, LOD, I-HOD, I-LOD

---

### Shift Bar / Candle Spike
**Definition**: 
- **Shift Bar/Candle**: The candle used to trap traders at higher and lower levels
- **Candle Spike**: An aggressive candle used to shift the trading zone and trigger stops

**Strategy Context**:
- Look for "shift bar", "shift candle", "candle spike"
- Often part of stop hunt pattern
- Used to identify trap moves

**Related Terms**: Stop hunt, trap move, M top, W bottom

---

### Brinks Trade
**Definition**: A type of trade that uses a timing element as part of the setup.

**Strategy Context**:
- Look for "brinks trade", "timing trade"
- Often combined with session opens
- May reference specific times or sessions

**Related Terms**: Session open, gap time, time mapping

---

## Position Management Terms

### Book a Profit
**Definition**: Closing all positions and taking a profit (you can also book a loss).

**Strategy Context**:
- Look for "book profit", "book a profit", "take profit"
- Part of position management
- May reference reset patterns

**Related Terms**: Reset, scratch, exit

---

### Scratch
**Definition**: A trade that doesn't produce, so you take what is given and close it.

**Strategy Context**:
- Look for "scratch trade", "scratch"
- Part of risk management
- Exiting at breakeven or small loss

**Related Terms**: Book a profit, exit

---

### On the Board
**Definition**: Having an open position.

**Strategy Context**:
- Reference to active trades
- Position management term

**Related Terms**: Open float, position management

---

### Open Float
**Definition**: The amount of equity tied up to manage your positions. Can be negative or positive.

**Strategy Context**:
- Position sizing and risk management
- May reference margin or account equity

**Related Terms**: On the board, position size

---

## Indicator Terms

### TDI (Trader's Dynamic Index)
**Definition**: An indicator developed by Dean Malone, used in conjunction with the market maker pattern.

**Strategy Context**:
- Look for "TDI", "Trader's Dynamic Index"
- Often used with MMM strategies
- May have specific rules or signals

**Related Terms**: Indicators, market maker pattern

---

### ADR (Average Daily Range)
**Definition**: An indicator that tracks average daily range of a currency.

**Strategy Context**:
- Used for position sizing or target setting
- May reference expected move size
- Helps identify extended moves

**Related Terms**: Indicators, market maker spread

---

### High/Low Marker
**Definition**: An indicator that tracks yesterday's high and low and plots it on today's chart.

**Strategy Context**:
- Used to identify key levels
- May reference previous day's range
- Helps with trading zone identification

**Related Terms**: HOD, LOD, high/low board

---

### High/Low Board
**Definition**: The board used by market makers to track the high and low of the day.

**Strategy Context**:
- Reference to HOD/LOD tracking
- Used by market makers
- May indicate key levels

**Related Terms**: HOD, LOD, high/low marker

---

## Market Structure Terms

### Market Maker
**Definition**: The group of people that have power and influence over the market. They have a huge equity base, control over the media, and influence in the political arena.

**Strategy Context**:
- Core concept of MMM methodology
- Understanding their behavior is key to strategy
- May reference their actions (stop hunts, position building, etc.)

**Related Terms**: All MMM terms relate to market maker behavior

---

### Market Sentiment
**Definition**: A feeling or belief that the market will behave a certain way, perpetuated by news and geopolitical events. It is not based on truth and has no bearing on how the market will actually perform.

**Strategy Context**:
- Contrasts with market maker trend
- May be used to identify contrarian opportunities
- Not reliable for strategy development

**Related Terms**: Market maker trend

---

### Net Change
**Definition**: The difference between the opening price and the current market price.

**Strategy Context**:
- Used to measure price movement
- May reference session or daily change
- Helps identify trend strength

**Related Terms**: Rise, correction, trend

---

## Trading Execution Terms

### Long Position
**Definition**: The act of buying.

**Strategy Context**:
- Standard trading term
- Used in entry rules

**Related Terms**: Short position, entry

---

### Short Position
**Definition**: The act of selling.

**Strategy Context**:
- Standard trading term
- Used in entry rules

**Related Terms**: Long position, entry

---

### Dealing Spread
**Definition**: The difference in pips between the bid and the ask. (The cost of doing business).

**Strategy Context**:
- Trading cost consideration
- May affect entry/exit timing
- Important for scalping strategies

**Related Terms**: Execution, trading costs

---

### Swap/Premium
**Definition**: Interest charges that accrue for holding an open position past the settlement time. Usually 5pm NYC, but varies by dealer/broker.

**Strategy Context**:
- Position holding cost
- May affect trade duration
- Important for swing trading

**Related Terms**: Position management, holding period

---

## Technical Terms

### Cross Pairs
**Definition**: Pairs comprised of majors other than the US dollar (e.g., EURGBP, EURJPY).

**Strategy Context**:
- Instrument selection
- May have different characteristics than major pairs
- May require different approach

**Related Terms**: Instruments, currency pairs

---

### Time Mapping
**Definition**: The action of matching your broker's server time to our indicators.

**Strategy Context**:
- Important for session-based strategies
- Ensures accurate timing
- May reference broker timezone

**Related Terms**: Session open, gap time, timing

---

## Strategy Identification Guide

### When Extracting Strategies, Look For:

1. **Chart Pattern Keywords**:
   - 22 trade, two-two, 2-2 → `22_trade`
   - Stop hunt, trap move, stop sweep, liquidity grab → `stop_hunt`
   - M top, W bottom, double top, double bottom → `m_w_reversal`
   - Counting levels, swing counting, leg counting → `counting_levels`
   - Blue box, trading zone, key zone, strike zone → `blue_box`
   - Straightaway, straight away → `straightaway`
   - Session open, kill zone, London session, NYC session → `session_open`

2. **Level References**:
   - I-HOD, I-LOD, HOD, LOD
   - Market maker spread (should be < 50 pips)
   - Trading zone (15-20 pips from HOD/LOD)

3. **Timing Elements**:
   - Session names (London, NYC, Asian)
   - Gap time references
   - Specific times (8:00 AM, etc.)

4. **Indicator References**:
   - TDI (Trader's Dynamic Index)
   - ADR (Average Daily Range)
   - High/Low markers

5. **Entry/Exit Logic**:
   - Stop hunt reversals
   - 22 trade setups
   - M/W formations at levels
   - Session open setups

---

## Notes for Strategy Database

- **Chart Pattern Field**: Use the mapped chart pattern IDs (e.g., `22_trade`, `stop_hunt`, `m_w_reversal`)
- **Strategy Type**: MMM strategies are often `reversal`, `trend_following`, or `swing` depending on the specific setup
- **Entry Setup Type**: Often `pattern_based` or `hybrid` (pattern + levels)
- **Timeframes**: Commonly 1H, 4H, D1 for MMM strategies
- **Instruments**: Often major pairs (EURUSD, GBPUSD, USDJPY) or cross pairs

---

**Copyright**: ©2007, Steve Mauro, Beat the Market Maker, Inc.  
**Enhanced for**: Algorithmic Trading System Strategy Database  
**Version**: 2.0 (Enhanced with chart pattern mappings and strategy identification guide)
