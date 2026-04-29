# FDL (Fibs Don't Lie) Glossary

**Source**: The Easiest Way to Trade! by FDL - Joseph Pena  
**Last Updated**: 2025-01-22  
**Purpose**: FDL strategy terminology for strategy identification and classification

---

## Core Concepts

### Tide Shift Pattern
**Definition**: A high-probability strategy with ideal risk/reward (typically 4:1). A compulsive move back to the 200EMA to stabilize price after a big down trend or up trend.

**Key Characteristics**:
- Not a trend reversal strategy (very risky)
- Correction move after trend confirmation
- Develops 2-3 times per week
- Works on 1H and 4H timeframes primarily
- Moves typically 50-70 pips
- Can work on any timeframe (fractal nature)

**Rules**:
1. Tide Shift complete upon touch of 200EMA
2. Avoid if already tested 200EMA (may be double/triple bottom)
3. Moving averages must be FLAT before crossing
4. Wait for retracement before entering (using Fib levels)

---

## Fibonacci Terms

### Fibonacci Retracement Levels
**Definition**: Key retracement zones used for entry in Tide Shift Pattern.

**Levels Used**:
- **0.382** (38.2%): First retracement zone
- **0.62** (62%): Second retracement zone (close to golden ratio)
- **0.705** (70.5%): Third retracement zone
- **0.79** (79%): Fourth retracement zone

**Usage**: Enter on retracement zone with confluence at resistance/support areas.

---

## Moving Averages

### 14EMA (14 Exponential Moving Average)
**Definition**: Fast-moving average used for trend direction and crossovers.

**Usage**:
- Trend direction identification
- Crosses with 50SMA signal Tide Shift entry
- Must be FLAT before crossing
- Used with 50SMA and 200EMA

### 50SMA (50 Simple Moving Average)
**Definition**: Medium-term moving average used as dynamic support/resistance.

**Usage**:
- Confluence with entries
- Stronger rejection than 14EMA
- Moves slower, market reacts more respectfully
- Must be FLAT before crossing with 14EMA

### 200EMA (200 Exponential Moving Average)
**Definition**: Long-term moving average - target for Tide Shift completion.

**Usage**:
- Tide Shift considered complete upon touch
- Stabilization point after big trends
- Target for price movement
- Used for partial profit taking

### FDL MA (FDL Moving Averages)
**Definition**: TradingView indicator that auto-populates all three moving averages (14EMA, 50SMA, 200EMA).

**Usage**: Search "FDL MA" in TradingView to add all three averages to chart.

---

## Market Structure Terms

### Market Structure Break
**Definition**: Strong move making new higher high or lower low, pointing to beginning of new cycle.

**Characteristics**:
- Similar to A, B, C, D structure
- Similar to Elliot Wave
- Identifies potential new cycle
- Used for Tide Shift identification

### Higher High / Lower Low
**Definition**: Market structure indicating trend direction.

**Usage**: Identifies beginning of potential new cycle for Tide Shift setup.

---

## Support and Resistance

### Static Support/Resistance
**Definition**: Key levels where price hesitates to cross or reach (magnetic areas).

**Characteristics**:
- Can attract or repel price
- Sharp moves bounce off them (ping pong reaction)
- Used with confluence for entries

### Dynamic Support/Resistance
**Definition**: Support/resistance controlled by moving averages, changing candle by candle.

**Characteristics**:
- Not static
- Controlled by moving average touches
- Higher moving average = stronger rejection
- 50SMA used as dynamic resistance/support

---

## Trading Concepts

### Confluence
**Definition**: Multiple factors aligning to increase probability of move in your direction.

**Components**:
- Market structure
- Trend direction
- Support/resistance
- Dynamic support/resistance
- Fibonacci levels

**Usage**: Strategy alone doesn't suffice - need confluence for high win rate.

### Fractals
**Definition**: Market structure patterns that repeat across timeframes.

**Usage**: 
- Move to 2 standard timeframes higher for trend direction
- Example: 15M structure break → check 1H for trend
- Tide Shift works on any timeframe but best on 1H/4H

### Retracement
**Definition**: Pullback in price before continuation.

**Usage**: Wait for retracement before entering Tide Shift, using Fibonacci levels.

---

## Risk Management

### Risk/Reward Ratio
**Definition**: Ratio of potential loss to potential profit.

**Tide Shift**: Typically 4:1 risk/reward due to strength of setup.

### Partial Profit Taking
**Definition**: Taking profit at 200EMA touch, moving stop to breakeven on remaining position.

**Usage**: Keeps risk out of account while allowing for continued move.

### Stop to Breakeven
**Definition**: Moving stop loss to entry price after partial profit taken.

**Usage**: Protects remaining position while allowing for continued profit.

---

## Timeframes

### Primary Timeframes
- **1 Hour (1H)**: Primary timeframe for Tide Shift
- **4 Hour (4H)**: Alternative primary timeframe
- **15 Minute (15M)**: Entry timeframe after structure break on higher timeframe

### Timeframe Rules
- Use 2 standard timeframes higher for trend direction
- Smaller timeframes = smaller impact
- 1H/4H best for day traders (in and out same day)

---

## Strategy Types

### Bullish Tide Shift
**Definition**: Tide Shift pattern in upward direction.

**Characteristics**:
- Price moves back to 200EMA after downtrend
- 14EMA crosses above 50SMA (both flat)
- Entry on retracement with confluence at support
- Target: Previous highs

### Bearish Tide Shift
**Definition**: Tide Shift pattern in downward direction.

**Characteristics**:
- Price moves back to 200EMA after uptrend
- 14EMA crosses below 50SMA (both flat)
- Entry on retracement with confluence at resistance
- Target: Previous lows

---

## Entry Rules

### Entry Conditions
1. Market structure break identified
2. Trend direction confirmed (14EMA, 50SMA, 200EMA alignment)
3. Moving averages FLAT before crossing
4. 14EMA crosses 50SMA
5. Retracement to Fibonacci level (.382, .62, .705, .79)
6. Confluence with support/resistance or dynamic support/resistance
7. Entry on 15M timeframe after higher timeframe confirmation

---

## Exit Rules

### Take Profit
- **Primary Target**: 200EMA touch (partial profit)
- **Secondary Target**: Previous highs/lows in area
- **Risk/Reward**: Typically 4:1

### Stop Loss
- Below/above recent swing for Bullish/Bearish Tide Shift
- Move to breakeven after 200EMA touch (partial profit taken)

---

## Integration with Strategy Database

### Classification Mapping

When extracting FDL strategies, look for:

1. **Indicators**:
   - `ema` - 14EMA
   - `sma` - 50SMA, 200EMA
   - `fibonacci` - Fibonacci retracements

2. **Chart Patterns**:
   - `fib_confluence` - Fibonacci confluence
   - `m_w_reversal` - Double tops/bottoms (part of setup)
   - `session_open` - Not typically used (intraday focus)

3. **Market Conditions**:
   - `trending` - After strong trends
   - `consolidation` - During retracement

4. **Trade Types**:
   - `tide_shift` - Can be added to trade_types taxonomy

5. **Methodology**:
   - `FDL` - Fibs Don't Lie methodology

---

**Note**: This glossary complements the MMM glossary and should be used together for comprehensive strategy identification.
