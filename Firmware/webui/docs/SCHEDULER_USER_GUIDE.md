# Scheduler System - User Guide

## Overview

The Mothbox Scheduler enables automated photo capture with flexible timing controls and event sequences. This guide covers the visual scheduler interface, trigger types, and real-world deployment scenarios.

### Purpose Statement

The scheduler system allows you to create automated capture sessions that run autonomously in the field, from simple fixed-time captures to complex multi-action sequences triggered by solar events, moon phases, or sensor conditions.

## Features

- **Visual Calendar Interface**: Create schedules using an intuitive calendar view
- **Multiple Trigger Types**: Interval, solar, moon phase, fixed time, and sensor-based triggers
- **Event Patterns**: Reusable action sequences with precise timing (e.g., lights on, photo, lights off)
- **Sub-hour Control**: Execute complex GPIO sequences within single cron intervals
- **Solar/Lunar Events**: Schedule relative to sunset, astronomical twilight, moon phases, and more
- **Expert Mode**: Direct cron expression editing for advanced users
- **Conflict Detection**: Automatic detection and resolution of scheduling conflicts
- **Deployment Integration**: Link schedules to deployment metadata for data management
- **Schedule Library**: Save, export, and reuse schedules across multiple Mothbox units

## Prerequisites

### Hardware Requirements
- Mothbox (Raspberry Pi 4 or 5)
- Arducam OwlSight camera
- GPIO-controlled lights (UV attract, flash)
- Real-time clock (RTC) for Pi 5 or PiJuice for Pi 4

### Software Requirements
- Mothbox Firmware v2.0+
- Web UI running (backend + frontend)
- GPS module configured (for solar/lunar triggers)

### Optional for Advanced Features
- BH1750/LTR303 light sensor (for light-level triggers)
- TMP102/MCP9808 temperature sensor (for temperature triggers)
- PIR motion sensor (for motion triggers)

---

## Quick Start

### 7-Step Workflow from Opening UI to Activating Schedule

1. **Open Web UI** and navigate to the Scheduler page
2. **Click "New Schedule"** button in the schedule list
3. **Enter schedule name** and description (e.g., "Summer Moth Survey")
4. **Select trigger type** from the dropdown (Interval, Solar, Moon Phase, Fixed Time, Sensor)
5. **Configure trigger settings** (time window, interval, offset, etc.)
6. **Add event patterns** with actions (attract_on, takephoto, attract_off)
7. **Click "Activate Schedule"** to apply and start autonomous operation

**Result**: Your Mothbox will now wake up, execute the scheduled actions, capture photos, and shut down automatically according to your schedule.

---

## Understanding the Two-Tier Model

The scheduler uses a two-tier architecture that separates **what happens** from **when it happens**.

### Event Patterns Explained

**Event Patterns** are reusable action sequences with relative timing. They define **what actions occur** and **in what order**.

**Structure**:
- Actions use offsets from pattern start (t=0)
- Multiple actions can be coordinated precisely
- Duration is calculated from the maximum offset

**Example: "UV Capture Cycle"**
```
Action 1: attract_on   at offset +0 minutes   (UV lights on)
Action 2: takephoto    at offset +5 minutes   (capture image)
Action 3: attract_off  at offset +15 minutes  (UV lights off)
Total duration: 15 minutes
```

This pattern ensures UV lights are on for 5 minutes before capture (allowing moths to settle), then remain on for 10 more minutes, with a total runtime of 15 minutes.

### Schedules Explained

**Schedules** define **when event patterns execute**. They contain:
- One or more embedded event patterns
- A trigger configuration (interval, solar, moon phase, etc.)
- Optional time windows and date constraints
- Deployment linkage

**Example: "Nightly Hourly Survey"**
```
Event Pattern: "UV Capture Cycle" (embedded)
Trigger: Interval (every 60 minutes)
Time Window: 21:00 to 05:00
Date Range: June 1 - August 31, 2024
Days: Every day
```

**Result**: The "UV Capture Cycle" pattern executes every hour from 9pm to 5am during the summer months.

### Why Two Tiers?

**Benefits of separation**:

1. **Reusability**: Create one "UV Capture Cycle" pattern, use it in multiple schedules (hourly, every 30 minutes, full moon only, etc.)

2. **Modularity**: Change trigger timing without recreating action sequences

3. **Portability**: Export schedules with patterns embedded as single JSON files, share between Mothbox units

4. **Clarity**: "What happens" (pattern) is conceptually separate from "when it happens" (schedule)

5. **Flexibility**: Combine multiple patterns in one schedule (e.g., "UV Capture" at top of hour, "Flash Photography" at half-hour)

---

## Trigger Types

The scheduler supports six trigger types, each suited for different research scenarios.

### Interval Trigger

**Purpose**: Execute event patterns every N minutes within a time window.

**Best for**: Regular sampling, consistent intervals, overnight surveys

**Configuration fields**:
- **Interval Minutes**: How often to repeat (1-10080 minutes, i.e., 1 minute to 7 days)
- **Time Window**: Start and end times (supports HH:MM or solar events)
- **Days of Week**: Optional restriction to specific weekdays (0=Monday, 6=Sunday)

**Example 1: Every 30 minutes from sunset to sunrise**
```
Interval: 30 minutes
Time Window:
  Start: sunset
  End: sunrise
  Start Offset: +30 minutes (start 30 min after sunset)
  End Offset: -30 minutes (stop 30 min before sunrise)
Days of Week: All days
```

**Example 2: Hourly captures on weekend nights**
```
Interval: 60 minutes
Time Window:
  Start: 21:00
  End: 05:00
Days of Week: Friday, Saturday (5, 6)
```

**Step-by-step setup**:
1. Select "Interval" trigger type
2. Enter interval in minutes (e.g., 60)
3. Set time window start (e.g., "21:00" or "sunset")
4. Set time window end (e.g., "05:00" or "sunrise")
5. Optionally add start/end offsets for solar times
6. Optionally restrict to specific days of week
7. Add event patterns to execute at each interval

### Solar Trigger

**Purpose**: Execute event patterns relative to sun position.

**Best for**: Crepuscular studies, twilight observations, consistent lighting conditions

**Solar events supported** (15 total):
- **dawn**: Dawn (sun 6° below horizon before sunrise)
- **sunrise**: Sun crosses horizon rising
- **noon**: Solar noon (highest point)
- **sunset**: Sun crosses horizon setting
- **dusk**: Dusk (sun 6° below horizon after sunset)
- **civil_dawn**: Civil twilight start (sun 6° below horizon, brightest twilight)
- **civil_dusk**: Civil twilight end (sun 6° below horizon)
- **nautical_dawn**: Nautical twilight start (sun 12° below horizon)
- **nautical_dusk**: Nautical twilight end (sun 12° below horizon)
- **astronomical_dawn**: Astronomical twilight start (sun 18° below horizon, darkest before total darkness)
- **astronomical_dusk**: Astronomical twilight end (sun 18° below horizon)
- **golden_hour_start**: Evening golden hour begins (sun near horizon, warm light)
- **golden_hour_end**: Morning golden hour ends
- **blue_hour_start**: Evening blue hour begins (deep twilight, blue tones)
- **blue_hour_end**: Morning blue hour ends

**Configuration fields**:
- **Solar Event**: Which sun position to trigger on
- **Offset Minutes**: +/- minutes from the event (-120 to +120)
- **Days of Week**: Optional weekday restriction

**Example 1: Capture at sunset+30 every day**
```
Solar Event: sunset
Offset: +30 minutes
Days of Week: All days
```
This triggers 30 minutes after sunset daily, adjusting automatically as sunset time changes throughout the year.

**Example 2: Astronomical twilight captures**
```
Solar Event: astronomical_dusk
Offset: 0 minutes
Days of Week: All days
```
Triggers when the sun is 18° below the horizon (true darkness begins), ideal for nocturnal species observation.

**GPS Requirements**: Solar triggers require GPS coordinates to calculate sun position. Ensure GPS module is configured and obtaining fixes.

**Step-by-step setup**:
1. Select "Solar" trigger type
2. Choose solar event from dropdown (e.g., "sunset")
3. Set offset in minutes (e.g., +30 for 30 minutes after)
4. Optionally restrict to specific days of week
5. Add event patterns to execute at the solar event

### Moon Phase Trigger

**Purpose**: Execute event patterns on specific lunar phases with offset days.

**Best for**: Lunar cycle studies, new moon/full moon observations, tidal research

**Moon phases supported** (8 total):
- **new**: New moon (0% illumination, moon not visible)
- **waxing_crescent**: Waxing crescent (1-49% illumination, growing)
- **first_quarter**: First quarter (50% illumination, half moon)
- **waxing_gibbous**: Waxing gibbous (51-99% illumination, growing)
- **full**: Full moon (100% illumination, fully visible)
- **waning_gibbous**: Waning gibbous (51-99% illumination, shrinking)
- **last_quarter**: Last quarter (50% illumination, half moon)
- **waning_crescent**: Waning crescent (1-49% illumination, shrinking)

**Configuration fields**:
- **Phases**: List of phases to trigger on (can select multiple)
- **Offset Days**: +/- days from exact phase (0-7 days)
- **Time Window**: Optional time window on phase days (supports HH:MM or solar events)

**Example 1: Full moon ±2 days, dusk to dawn**
```
Phases: full
Offset Days: 2 (captures 2 days before, day of, 2 days after = 5 days total)
Time Window:
  Start: dusk
  End: dawn
```
Captures during the 5-day window around full moon, only from dusk to dawn each night.

**Example 2: New moon only, all night**
```
Phases: new
Offset Days: 0 (only on exact new moon night)
Time Window:
  Start: 21:00
  End: 06:00
```

**Example 3: All quarter phases, no time restriction**
```
Phases: first_quarter, last_quarter
Offset Days: 1
Time Window: None
```
Captures on first and last quarter moons (±1 day), any time of day.

**Step-by-step setup**:
1. Select "Moon Phase" trigger type
2. Select one or more phases from checkboxes
3. Set offset days (e.g., 2 for ±2 days)
4. Optionally add time window to restrict to specific hours
5. Add event patterns to execute on phase days

### Fixed Time Trigger

**Purpose**: Execute event patterns at specific clock time(s) daily.

**Best for**: Simple daily routines, consistent time-of-day sampling, baseline captures

**Configuration fields**:
- **Time**: Fixed time in HH:MM format (24-hour)
- **Days of Week**: Optional weekday restriction

**Example 1: Every night at 9:30pm**
```
Time: 21:30
Days of Week: All days
```

**Example 2: Weekday mornings only**
```
Time: 08:00
Days of Week: Monday, Tuesday, Wednesday, Thursday, Friday (0, 1, 2, 3, 4)
```

**Example 3: Multiple fixed times using multiple schedules**
```
Schedule A: Time 21:00 (9pm)
Schedule B: Time 23:00 (11pm)
Schedule C: Time 01:00 (1am)
Schedule D: Time 03:00 (3am)
```
Note: Only one schedule can be active at a time. For multiple times, use Interval trigger instead, or create separate schedules and manually switch between them.

**Step-by-step setup**:
1. Select "Fixed Time" trigger type
2. Enter time in HH:MM format (e.g., 21:30)
3. Optionally restrict to specific days of week
4. Add event patterns to execute at that time

### Sensor Trigger

**Purpose**: Execute event patterns when sensor readings meet threshold conditions.

**Best for**: Activity-based capture, environmental condition monitoring, adaptive sampling

**Supported sensors**:
- **motion**: PIR motion sensor (triggers on detection, threshold ignored)
- **light**: BH1750/LTR303 lux sensor (triggers when light level crosses threshold)
- **temperature**: TMP102/MCP9808 temperature sensor (triggers on temperature threshold)

**Comparison operators**:
- **gt**: Greater than (e.g., temperature > 20°C)
- **lt**: Less than (e.g., light < 100 lux)
- **eq**: Equal to
- **gte**: Greater than or equal to
- **lte**: Less than or equal to

**Configuration fields**:
- **Sensor Type**: Which sensor to read
- **Threshold**: Numeric threshold value (ignored for motion sensor)
- **Comparison**: Operator to use (gt, lt, eq, gte, lte)
- **Cooldown Minutes**: Minimum time between triggers (1-60 minutes)
- **Time Window**: Optional time window to restrict sensor checking

**Example 1: Motion detection at night**
```
Sensor Type: motion
Threshold: 0 (ignored for motion)
Comparison: gt (ignored for motion)
Cooldown: 5 minutes
Time Window:
  Start: 21:00
  End: 06:00
```
Triggers on any motion detection between 9pm-6am, with 5-minute cooldown to prevent rapid repeated triggers.

**Example 2: Low-light capture**
```
Sensor Type: light
Threshold: 100
Comparison: lt (less than)
Cooldown: 10 minutes
Time Window: None
```
Triggers when ambient light drops below 100 lux, checking continuously with 10-minute cooldown.

**Example 3: Temperature-based activation**
```
Sensor Type: temperature
Threshold: 15
Comparison: gte (greater than or equal)
Cooldown: 30 minutes
Time Window:
  Start: sunset
  End: sunrise
```
Triggers when temperature is ≥15°C during nighttime hours, checking every 30 minutes.

**Hardware Requirements**: Sensor triggers require the corresponding I2C sensor to be connected and configured in `controls.txt`.

**Step-by-step setup**:
1. Select "Sensor" trigger type
2. Choose sensor type (motion, light, temperature)
3. Set threshold value (for light/temperature sensors)
4. Choose comparison operator
5. Set cooldown period in minutes
6. Optionally add time window to restrict checking hours
7. Add event patterns to execute when sensor condition is met

### Cron Expression (Expert Mode)

**Purpose**: Direct cron expression editing for maximum flexibility and advanced patterns.

**Best for**: Complex schedules not covered by visual triggers, legacy cron migration, power users

**Cron Syntax**: Standard 5-field cron expression
```
┌─────── minute (0-59)
│ ┌───── hour (0-23)
│ │ ┌─── day of month (1-31)
│ │ │ ┌─ month (1-12)
│ │ │ │ ┌ day of week (0-7, 0 and 7 are Sunday)
│ │ │ │ │
* * * * *
```

**Common Cron Examples**:

| Schedule Pattern | Cron Expression | Description |
|------------------|-----------------|-------------|
| Every hour | `0 * * * *` | At minute 0 of every hour |
| Every 30 minutes | `*/30 * * * *` | Every 30 minutes |
| Every night at 9pm | `0 21 * * *` | At 9:00 PM every day |
| Every night 9pm-5am | `0 21-23,0-5 * * *` | Top of each hour from 9pm to 5am |
| Weekends only at 10pm | `0 22 * * 5,6` | At 10:00 PM on Friday and Saturday |
| Every 15 min (1-5am) | `*/15 1-5 * * *` | Every 15 minutes from 1am to 5am |
| Monthly on 1st (midnight) | `0 0 1 * *` | At midnight on the first day of month |

**Special Characters**:
- `*` (asterisk): Any value (e.g., `* * * * *` = every minute)
- `,` (comma): List separator (e.g., `0,30 * * * *` = minute 0 and 30)
- `-` (hyphen): Range (e.g., `0 9-17 * * *` = 9am to 5pm)
- `/` (slash): Step values (e.g., `*/15 * * * *` = every 15 minutes)

**Validation**: The UI validates cron expressions and shows errors for invalid syntax. The system checks:
- Exactly 5 fields
- Valid numeric ranges
- Proper special character usage
- Security constraints (no shell commands, only whitelisted scripts)

**Step-by-step Expert Mode**:
1. Click "Enable Expert Mode" toggle in schedule editor
2. Visual trigger fields are hidden, cron expression field appears
3. Enter 5-field cron expression (e.g., `0 21 * * *`)
4. Validation feedback appears in real-time
5. Add event patterns to execute at cron-defined times
6. Save and activate schedule

**Converting from visual triggers**: When enabling Expert Mode on an existing schedule, the system shows the generated cron expression. You can then edit it directly for fine-tuning.

---

## Creating Your First Schedule

This section provides a complete walkthrough of creating a schedule from start to finish.

### Step 1: Navigate and Click New Schedule

1. Open the Mothbox Web UI in your browser (e.g., `http://mothbox.local:5000`)
2. Click "Scheduler" in the main navigation menu
3. The Scheduler page displays with:
   - Left panel: Schedule list (currently empty)
   - Right panel: Calendar view (empty until schedule created)
4. Click the **"New Schedule"** button at the top of the schedule list

Result: A schedule editor drawer opens on the right side of the screen.

### Step 2: Enter Name and Description

In the schedule editor drawer:

1. **Name field**: Enter a clear, descriptive name
   - Example: "Summer Moth Survey 2024"
   - Best practice: Include purpose and date range in name

2. **Description field** (optional): Add detailed notes
   - Example: "Nightly captures from sunset to sunrise during peak moth season (June-August). UV attract lights on 5min before capture."
   - Best practice: Document research goals, expected species, special conditions

Click "Next" or scroll down to continue.

### Step 3: Select Trigger Type

In the Trigger Type section:

1. Five trigger type cards are displayed:
   - **Interval**: "Every N minutes"
   - **Solar**: "Relative to sun position"
   - **Moon Phase**: "On lunar phases"
   - **Fixed Time**: "Specific clock time"
   - **Sensor**: "When sensor conditions met"

2. Click a card to select that trigger type
   - Card highlights with blue border when selected
   - Trigger configuration fields appear below

3. For this example, select **"Interval"**

### Step 4: Configure Trigger Settings

For an Interval trigger (our example):

1. **Interval Minutes**: Enter `60` (for hourly captures)

2. **Time Window Start**:
   - Click the dropdown
   - Choose "Solar Event" tab
   - Select "sunset"
   - Offset: Enter `30` (for 30 minutes after sunset)

3. **Time Window End**:
   - Click the dropdown
   - Choose "Solar Event" tab
   - Select "sunrise"
   - Offset: Enter `0` (no offset)

4. **Days of Week**: Leave all days checked (or uncheck specific days to restrict)

5. **Date Range** (optional):
   - Start Date: Click calendar icon, select June 1, 2024
   - End Date: Click calendar icon, select August 31, 2024

Result: Schedule is configured to run hourly from 30 minutes after sunset to sunrise, June-August 2024.

### Step 5: Add Event Patterns with Actions

In the Event Patterns section:

1. Click **"Add Event Pattern"** button
2. Pattern editor opens

3. **Pattern Name**: Enter "UV Capture Cycle"

4. **Pattern Description** (optional): "Turn on UV lights, wait 5 minutes, capture photo, keep lights on 15 minutes total"

5. **Add first action**:
   - Click "Add Action" button
   - Action Type: Select "gpio"
   - Action Name: Select "attract_on"
   - Offset Minutes: Enter `0`
   - Description: "Turn on UV attract lights"
   - Click "Save Action"

6. **Add second action**:
   - Click "Add Action" button
   - Action Type: Select "camera"
   - Action Name: Select "takephoto"
   - Offset Minutes: Enter `5`
   - Description: "Capture photo after 5 min settling time"
   - Click "Save Action"

7. **Add third action**:
   - Click "Add Action" button
   - Action Type: Select "gpio"
   - Action Name: Select "attract_off"
   - Offset Minutes: Enter `15`
   - Description: "Turn off UV lights"
   - Click "Save Action"

8. Pattern duration shows: "15 minutes"

9. Click "Save Pattern"

Result: Event pattern "UV Capture Cycle" is added to the schedule. The pattern will execute at each hourly trigger.

### Step 6: Set Date Range (Optional)

If not already set in Step 4:

1. Scroll to Date Constraints section
2. **Start Date**: Click calendar, select June 1, 2024
3. **End Date**: Click calendar, select August 31, 2024
4. Leave blank for no date restrictions

### Step 7: Preview and Validate

Before saving:

1. Click **"Preview Schedule"** button
2. Preview panel shows:
   - Next 10 execution times calculated
   - Pattern actions with timestamps
   - Total runtime per execution
   - Potential conflicts highlighted

3. Review the preview:
   - First execution: `2024-06-01 20:37:30` (sunset+30 on June 1)
   - Actions: UV on at :30, photo at :35, UV off at :45
   - Next execution: `2024-06-01 21:37:30` (60 minutes later)
   - Pattern continues hourly until sunrise

4. **Validation errors** appear if any:
   - Missing required fields (name, trigger config, patterns)
   - Invalid time formats
   - Conflicting settings
   - Fix any errors before proceeding

### Step 8: Save and Activate

1. Click **"Save Schedule"** button at bottom of editor
   - Schedule is saved to `CONFIG_DIR/schedules/{id}.json`
   - Schedule appears in schedule list (left panel)
   - Status: "Inactive" (not yet active)

2. To activate the schedule:
   - Click the schedule in the list to select it
   - Click **"Activate Schedule"** button
   - Confirmation dialog appears

3. **Activation dialog** shows:
   - Schedule summary
   - Deployment options (optional):
     - "Create new deployment" checkbox
     - Deployment name field (auto-filled with schedule name)
   - Warning if another schedule is currently active
   - "Confirm Activation" button

4. Optionally check "Create new deployment" to link schedule to deployment metadata

5. Click **"Confirm Activation"**

6. System performs activation:
   - Deactivates any currently active schedule
   - Validates schedule (conflict check)
   - Writes cron expression to system
   - Sets RTC wakealarm for next wakeup
   - Creates deployment metadata if requested
   - Marks schedule as active

7. Success message appears: "Schedule activated successfully"
   - Schedule status changes to "Active" (green badge)
   - Calendar view populates with scheduled executions
   - Next wakeup time displayed

Result: Your Mothbox is now scheduled to wake up, execute the UV Capture Cycle pattern hourly from sunset+30 to sunrise during June-August 2024, then shut down automatically.

---

## Action Types Reference

Actions are the building blocks of event patterns. Each action type controls a specific hardware subsystem or triggers a software function.

| Action Type | Action Name | Description |
|-------------|-------------|-------------|
| **gpio** | `attract_on` | Turn on UV attract lights (GPIO relay) |
| **gpio** | `attract_off` | Turn off UV attract lights (GPIO relay) |
| **gpio** | `flash_on` | Turn on flash lights (GPIO relay) |
| **gpio** | `flash_off` | Turn off flash lights (GPIO relay) |
| **camera** | `takephoto` | Capture photo using TakePhoto.py script (supports HDR, focus bracketing, GPS tagging) |
| **gps_sync** | `gps_sync` | Synchronize system time with GPS module |
| **service** | `backup` | Run system backup routine |
| **service** | `update_display` | Update e-paper display with current status |

**Action Parameters**: Some actions accept optional parameters in the `parameters` field (JSON object):

- **takephoto parameters**:
  - `hdr_mode`: Boolean, enable HDR bracketing
  - `focus_bracket`: Boolean, enable focus stacking sequence
  - `bracket_count`: Integer, number of images in bracket sequence

- **gpio parameters**: None currently

- **gps_sync parameters**: None currently

- **service parameters**: Vary by service

**Example action with parameters**:
```json
{
  "action_type": "camera",
  "action_name": "takephoto",
  "offset_minutes": 5,
  "parameters": {
    "hdr_mode": true,
    "bracket_count": 3
  },
  "description": "Capture 3-image HDR bracket"
}
```

---

## Working with Event Patterns

Event patterns are the core building blocks that define action sequences.

### Creating Custom Patterns

To create a new event pattern:

1. In the schedule editor, click **"Add Event Pattern"**
2. Enter **Pattern Name** (required, max 200 characters)
3. Enter **Pattern Description** (optional, max 2000 characters)
4. **Add actions** (at least 1 required, max 20 per pattern):
   - Click "Add Action"
   - Select action type and name
   - Set offset minutes (0-1440, i.e., 0 to 24 hours)
   - Add description
   - Click "Save Action"
5. Repeat to add more actions
6. Click **"Save Pattern"**

The pattern is embedded in the schedule and saved as part of the schedule JSON file.

### Using Built-in Patterns

The system includes several built-in patterns for common workflows:

**Built-in patterns** (located in `webui/backend/presets_builtin/patterns/`):

- **Simple Capture**: Single photo capture with no lights
- **UV Capture Cycle**: UV on, photo, UV off (standard moth trap sequence)
- **Flash Photography**: Flash on, photo, flash off
- **GPS Sync Sequence**: GPS sync, wait, capture with synced time
- **Extended UV Session**: UV on 30 minutes, multiple photos, UV off

To use a built-in pattern:

1. Click "Use Built-in Pattern" button
2. Select pattern from dropdown
3. Pattern actions are added to your schedule
4. Optionally edit offsets or add/remove actions
5. Save the modified pattern with your schedule

### Pattern Examples with JSON

Below are complete JSON examples showing pattern structure.

#### Example 1: UV Capture Cycle

```json
{
  "pattern_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "UV Capture Cycle",
  "description": "Standard moth trap sequence: UV lights on, 5min settling, capture, 15min total runtime",
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "offset_minutes": 0,
      "parameters": {},
      "description": "Turn on UV attract lights"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 5,
      "parameters": {},
      "description": "Capture photo after settling time"
    },
    {
      "action_type": "gpio",
      "action_name": "attract_off",
      "offset_minutes": 15,
      "parameters": {},
      "description": "Turn off UV lights"
    }
  ],
  "category": "user",
  "tags": ["uv", "moth", "standard"],
  "duration_minutes": 15
}
```

#### Example 2: Flash Photography

```json
{
  "pattern_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "name": "Flash Photography",
  "description": "Quick capture with flash illumination, minimal runtime",
  "actions": [
    {
      "action_type": "gpio",
      "action_name": "flash_on",
      "offset_minutes": 0,
      "parameters": {},
      "description": "Turn on flash"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 0,
      "parameters": {},
      "description": "Immediate capture with flash"
    },
    {
      "action_type": "gpio",
      "action_name": "flash_off",
      "offset_minutes": 1,
      "parameters": {},
      "description": "Turn off flash after capture"
    }
  ],
  "category": "built-in",
  "tags": ["flash", "quick"],
  "duration_minutes": 1
}
```

#### Example 3: GPS Sync Sequence

```json
{
  "pattern_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "name": "GPS Sync Sequence",
  "description": "Synchronize time with GPS before capture for accurate timestamps",
  "actions": [
    {
      "action_type": "gps_sync",
      "action_name": "gps_sync",
      "offset_minutes": 0,
      "parameters": {},
      "description": "Sync system time with GPS"
    },
    {
      "action_type": "gpio",
      "action_name": "attract_on",
      "offset_minutes": 2,
      "parameters": {},
      "description": "Turn on UV lights after GPS lock"
    },
    {
      "action_type": "camera",
      "action_name": "takephoto",
      "offset_minutes": 7,
      "parameters": {},
      "description": "Capture with accurate timestamp"
    },
    {
      "action_type": "gpio",
      "action_name": "attract_off",
      "offset_minutes": 17,
      "parameters": {},
      "description": "Turn off UV lights"
    }
  ],
  "category": "user",
  "tags": ["gps", "accuracy"],
  "duration_minutes": 17
}
```

---

## Using Expert Mode (Cron)

Expert Mode allows direct editing of cron expressions for maximum flexibility.

### How to Enable Expert Mode Toggle

1. Open schedule editor (new or existing schedule)
2. In the Trigger Type section, locate the **"Expert Mode"** toggle switch
3. Click the toggle to enable
4. Visual trigger fields disappear
5. **Cron Expression** text field appears

**Reverting to visual mode**: Toggle off Expert Mode. If a valid cron was entered, the system attempts to convert it back to a visual trigger type. Complex crons that cannot be represented visually will show a warning.

### Cron Syntax Diagram

Standard 5-field cron expression:

```
┌─────────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌─────────── day of month (1-31)
│ │ │ ┌───────── month (1-12)
│ │ │ │ ┌─────── day of week (0-7, 0 and 7 are Sunday)
│ │ │ │ │
* * * * *
```

**Field meanings**:
- **Minute**: 0-59
- **Hour**: 0-23 (24-hour format)
- **Day of Month**: 1-31
- **Month**: 1-12 (1=January)
- **Day of Week**: 0-7 (0=Sunday, 1=Monday, ..., 6=Saturday, 7=Sunday)

**Special characters**:
- `*`: Any value (e.g., `* * * * *` runs every minute)
- `,`: Value list (e.g., `0,30 * * * *` runs at minute 0 and 30)
- `-`: Range (e.g., `0-15 * * * *` runs minutes 0 through 15)
- `/`: Step values (e.g., `*/15 * * * *` runs every 15 minutes)

### Common Cron Examples Table

| Pattern | Cron Expression | Description |
|---------|-----------------|-------------|
| **Every hour** | `0 * * * *` | At minute 0 of every hour (e.g., 1:00, 2:00, 3:00...) |
| **Every 30 minutes** | `*/30 * * * *` | At minute 0 and 30 of every hour |
| **Every 15 minutes** | `*/15 * * * *` | At minutes 0, 15, 30, 45 of every hour |
| **Every 5 minutes** | `*/5 * * * *` | At minutes 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 |
| **Daily at 9pm** | `0 21 * * *` | At 9:00 PM every day |
| **Nightly (9pm-5am)** | `0 21-23,0-5 * * *` | Top of each hour from 9pm through 5am |
| **Every night at 9pm and 3am** | `0 21,3 * * *` | At 9:00 PM and 3:00 AM every day |
| **Weekends at 10pm** | `0 22 * * 5,6` | At 10:00 PM on Friday and Saturday |
| **Weekdays at 8am** | `0 8 * * 1-5` | At 8:00 AM Monday through Friday |
| **Monthly on 1st** | `0 0 1 * *` | At midnight on the first day of each month |
| **Hourly (business hours)** | `0 9-17 * * 1-5` | At the top of each hour from 9am-5pm, Monday-Friday |
| **Every 2 hours** | `0 */2 * * *` | At minute 0, every 2 hours (midnight, 2am, 4am...) |

### Validation Behavior

The cron expression field validates in real-time:

**Valid expression indicators**:
- Green checkmark icon appears
- "Valid cron expression" message
- Preview button becomes enabled

**Invalid expression indicators**:
- Red X icon appears
- Error message explains the issue
- Save button remains disabled

**Common validation errors**:
- "Must have exactly 5 fields" - check for missing or extra spaces
- "Invalid minute value" - minute must be 0-59
- "Invalid hour value" - hour must be 0-23
- "Invalid day of month" - day must be 1-31
- "Invalid month" - month must be 1-12
- "Invalid day of week" - day must be 0-7

**Security validation**: The system checks that the cron expression only triggers whitelisted scripts (no arbitrary shell commands allowed).

### Example: Converting Visual to Cron

**Visual trigger** (Interval):
```
Interval: 60 minutes
Time Window: 21:00 to 05:00
Days: All days
```

**Enable Expert Mode** → Shows generated cron:
```
0 21-23,0-5 * * *
```

**Explanation**:
- `0`: Minute 0 (top of hour)
- `21-23,0-5`: Hours 21, 22, 23, 0, 1, 2, 3, 4, 5 (9pm-5am)
- `*`: Every day of month
- `*`: Every month
- `*`: Every day of week

**Edit cron** to add 1am and 3am only:
```
0 1,3 * * *
```

**Save** - now executes only at 1:00 AM and 3:00 AM instead of hourly.

---

## Calendar View Usage

The calendar view provides visual feedback on scheduled executions.

### Navigating Week/Month View

**View toggle**:
- **Week View**: Shows 7 days in detail with hourly breakdown
- **Month View**: Shows 28-31 days with daily summary

**Navigation controls**:
- **Previous/Next arrows**: Move backward/forward by week or month
- **Today button**: Jump to current date
- **Date picker**: Click calendar icon to jump to specific date

**Zoom controls** (Week View only):
- **+ button**: Zoom in (show more detail)
- **- button**: Zoom out (show less detail)

### Understanding Execution Markers

Scheduled executions appear as colored markers on the calendar:

**Marker types**:
- **Blue dot**: Single execution scheduled
- **Blue badge with number**: Multiple executions on that day (e.g., "8" means 8 executions)
- **Green outline**: Execution is today
- **Gray dot**: Past execution (already completed)
- **Red outline**: Conflicting execution (overlaps with another schedule)

**Week View details**:
- Markers appear on specific hour rows
- Hover over marker to see tooltip with time and pattern name
- Click marker to view full execution details

**Month View details**:
- Markers appear in day cells
- Number badge shows total executions for that day
- Click day to expand and see all executions

### Viewing Execution Details

**Click an execution marker** to open the Execution Detail panel:

**Panel contents**:
- **Execution Time**: Exact timestamp (e.g., "2024-06-15 21:37:30")
- **Schedule Name**: Which schedule is executing
- **Event Patterns**: List of patterns with action timelines
- **Actions**: Expanded list showing:
  - Action type and name
  - Absolute timestamp
  - Description
  - Parameters (if any)
- **Duration**: Total runtime for this execution
- **Status**: Pending, Completed, or Failed (for past executions)

**Example detail view**:
```
Execution: June 15, 2024 at 21:37:30
Schedule: Summer Moth Survey 2024
Pattern: UV Capture Cycle

Actions:
  21:37:30 - GPIO: attract_on (Turn on UV lights)
  21:42:30 - Camera: takephoto (Capture after settling)
  21:52:30 - GPIO: attract_off (Turn off UV lights)

Duration: 15 minutes
Status: Pending
```

**Close panel**: Click X icon or click outside panel

---

## Schedule Management

### Editing Existing Schedules

To edit a saved schedule:

1. Click the schedule in the schedule list (left panel)
2. Schedule details appear in main view
3. Click **"Edit Schedule"** button
4. Schedule editor drawer opens with all fields populated
5. Modify any fields:
   - Name, description
   - Trigger type and settings
   - Event patterns (add, edit, remove, reorder)
   - Date range
   - Deployment linkage
6. Click **"Save Changes"**
7. If schedule is active, you'll see a warning: "This schedule is active. Saving changes will require re-activation."
8. Confirm to save

**Note**: Editing an active schedule automatically deactivates it. You must re-activate after saving changes.

### Duplicating Schedules

To create a copy of an existing schedule:

1. Click the schedule in the list
2. Click **"Duplicate Schedule"** button (icon: two overlapping squares)
3. A copy is created with:
   - Name: "Copy of [Original Name]"
   - All settings duplicated
   - New unique schedule_id
   - Status: Inactive
4. Edit the duplicate to customize
5. Activate when ready

**Use case**: Create variations of a schedule (e.g., "Summer Moth Survey" → "Fall Moth Survey" with different date range).

### Enabling/Disabling Without Deleting

To temporarily disable a schedule without losing it:

1. Click the schedule in the list
2. Toggle the **"Enabled"** switch to OFF
3. Schedule status changes to "Disabled" (gray badge)
4. Disabled schedules:
   - Cannot be activated
   - Do not appear in conflict checks
   - Are hidden from calendar view
   - Remain saved in schedule files

To re-enable:

1. Click the disabled schedule
2. Toggle **"Enabled"** switch to ON
3. Schedule status changes to "Inactive" (ready to activate)

**Use case**: Seasonal schedules (disable winter schedules during summer, re-enable in fall).

### Deleting Schedules (Built-in Protection)

To permanently delete a schedule:

1. Click the schedule in the list
2. Click **"Delete Schedule"** button (trash icon)
3. **Confirmation dialog** appears with warnings:
   - "This action cannot be undone"
   - "Schedule will be permanently deleted from disk"
   - If active: "This schedule is currently active and will be deactivated"
   - If has deployments linked: "X deployments reference this schedule"
4. Type the schedule name to confirm deletion
5. Click **"Confirm Delete"**

**Built-in protections**:
- Active schedules show extra warning
- Deployments linked to schedule are preserved (only schedule is deleted)
- Schedule file is deleted from `CONFIG_DIR/schedules/`
- No recovery after deletion (export schedule first if unsure)

**Export before deleting**: Click "Export Schedule" button to download JSON file for backup.

---

## Activating and Deactivating

### Only One Schedule Active at a Time

The Mothbox scheduling system enforces a **single active schedule** constraint:

**Reason**: The hardware (RTC, cron, GPIO) can only follow one schedule at a time. Multiple concurrent schedules would conflict.

**Behavior**:
- When you activate a schedule, any currently active schedule is automatically deactivated
- The system shows a warning before activation if another schedule is active
- Only one schedule has "Active" status (green badge) in the list
- All others show "Inactive" (gray badge)

**Managing multiple schedules**:
- Create multiple schedules for different scenarios (e.g., "Summer", "Winter", "Full Moon Only")
- Manually switch between them by activating the desired schedule
- Export/import schedules to share configurations

### Activation Process (Validation → Conflict Check → Cron Applied → RTC Set)

When you click "Activate Schedule", the system performs a multi-step activation:

#### Phase 1: Validation

**Checks**:
- Schedule has valid name and description
- At least one event pattern with actions
- Trigger configuration is complete and valid
- Date range is valid (start ≤ end)
- No validation errors in any field

**Failure**: If validation fails, activation is blocked and errors are displayed. Fix errors and try again.

#### Phase 2: Conflict Check

**Checks**:
- No overlap with currently active schedule (if any)
- No resource conflicts (e.g., two schedules trying to control same GPIO pins simultaneously)
- RTC/cron can represent the schedule (some complex patterns may not be directly supported)

**Failure**: If conflicts detected, a conflict resolution dialog appears showing:
- Which schedule conflicts
- What the conflict is (time overlap, resource conflict)
- Options: "Deactivate conflicting schedule" or "Cancel activation"

**Resolution**: Choose to deactivate the conflicting schedule and proceed, or cancel.

#### Phase 3: Apply to System (Cron + CSV)

**Actions**:
1. Generate cron expression(s) from schedule trigger
2. Write to `schedule_settings.csv`:
   - Cron minute field
   - Cron hour field
   - Cron weekday field
   - Active status
3. Create/update system cron jobs via `python-crontab` library
4. Validate cron was applied correctly

**Failure**: If cron application fails (e.g., permission error), activation is rolled back and error message shown.

#### Phase 4: Set RTC Wakealarm

**Actions**:
1. Calculate next scheduled execution time from cron expression
2. Convert to Unix epoch timestamp
3. Clear existing RTC wakealarm: `echo 0 > /sys/class/rtc/rtc0/wakealarm`
4. Set new wakealarm: `echo [epoch] > /sys/class/rtc/rtc0/wakealarm`
5. Update `controls.txt` with next wake time for reference

**Pi 4 with PiJuice**: Uses PiJuice API to set wakeup alarm instead of RTC file

**Failure**: If RTC set fails, activation is rolled back. Check system logs.

#### Phase 5: Deployment (Optional)

**If** `create_deployment: true` was set:
1. Create deployment metadata file in photos directory
2. Populate with schedule details:
   - Name, date range, location (if GPS available)
   - Link to schedule_id
3. Deployment appears in Deployment Manager

#### Phase 6: Mark Active

**Actions**:
1. Deactivate any previously active schedule (set `is_active: false`)
2. Set current schedule `is_active: true`
3. Write schedule JSON file
4. Update schedule list in UI
5. Show success message: "Schedule activated successfully"

**Result**: The schedule is now controlling the Mothbox. System will wake at scheduled times and execute event patterns.

### Deactivation and Cleanup

To manually deactivate a schedule:

1. Click the active schedule in the list
2. Click **"Deactivate Schedule"** button
3. Confirmation dialog appears
4. Click **"Confirm Deactivation"**

**Deactivation process**:
1. Clear cron jobs (remove from system cron)
2. Clear RTC wakealarm: `echo 0 > /sys/class/rtc/rtc0/wakealarm`
3. Write empty `schedule_settings.csv` or set active=false
4. Mark schedule as `is_active: false`
5. Update schedule list (no active schedule)

**Result**: Mothbox stops automatic wakeups. System remains powered until manually activated again or new schedule activated.

**Automatic deactivation scenarios**:
- Schedule end date reached (deactivates itself)
- Another schedule activated (previous auto-deactivates)
- System detects schedule errors (safe deactivation)

---

## Real-World Scenario Examples

### Example 1: Summer Moth Survey

**Research Goal**: Survey moth diversity during peak activity season (June-August), capturing hourly from sunset to sunrise.

**Complete Walkthrough**:

#### Step 1: Plan the Schedule

**Requirements**:
- **Duration**: June 1 - August 31, 2024 (3 months)
- **Timing**: Sunset+30 minutes to sunrise (accounts for changing day length)
- **Interval**: Every 30 minutes (balanced between coverage and power)
- **Actions**: UV lights on 5 minutes before capture for moth attraction

#### Step 2: Create Schedule

1. Navigate to Scheduler page
2. Click "New Schedule"
3. Enter name: `Summer Moth Survey 2024`
4. Enter description: `Comprehensive moth diversity survey during peak activity season. Captures every 30 minutes from sunset to sunrise. UV attract lights provide 5-minute settling period.`

#### Step 3: Configure Interval Trigger

1. Select trigger type: **Interval**
2. Set interval: `30` minutes
3. Set time window start:
   - Type: Solar Event
   - Event: `sunset`
   - Offset: `+30` minutes (start 30 min after sunset)
4. Set time window end:
   - Type: Solar Event
   - Event: `sunrise`
   - Offset: `0` minutes (stop at sunrise)
5. Days of week: All days selected
6. Date range:
   - Start: `2024-06-01`
   - End: `2024-08-31`

**Why these settings?**:
- Sunset+30 ensures civil twilight has passed (darker conditions)
- Every 30 minutes provides 10-16 captures per night (depending on season)
- Date range covers Northern Hemisphere peak moth season

#### Step 4: Create Event Pattern

1. Click "Add Event Pattern"
2. Pattern name: `UV Capture Cycle`
3. Pattern description: `Standard moth trap sequence with settling time`
4. Add actions:

**Action 1: UV On**
- Type: `gpio`
- Name: `attract_on`
- Offset: `0` minutes
- Description: `Turn on UV attract lights`

**Action 2: Capture**
- Type: `camera`
- Name: `takephoto`
- Offset: `5` minutes
- Description: `Capture after 5-minute settling period`

**Action 3: UV Off**
- Type: `gpio`
- Name: `attract_off`
- Offset: `15` minutes
- Description: `Turn off UV lights`

5. Save pattern (duration: 15 minutes)

#### Step 5: Preview Results

Click "Preview Schedule":

```
Next 10 Executions:

1. 2024-06-01 20:37:30
   - 20:37:30: UV lights on
   - 20:42:30: Capture photo
   - 20:52:30: UV lights off

2. 2024-06-01 21:07:30
   - 21:07:30: UV lights on
   - 21:12:30: Capture photo
   - 21:22:30: UV lights off

3. 2024-06-01 21:37:30
   (pattern repeats every 30 minutes until sunrise at ~06:15)

Total: ~11 captures per night in June
Total: ~10 captures per night in August (shorter nights)
Estimated: 1,000 photos over 3-month survey
```

#### Step 6: Link to Deployment

1. Check "Create new deployment"
2. Deployment name: `Summer Moth Survey 2024`
3. Location: Let GPS auto-fill coordinates
4. Environmental conditions (optional): `{"habitat": "mixed forest", "elevation": "350m"}`

#### Step 7: Activate

1. Click "Save Schedule"
2. Click "Activate Schedule"
3. Confirm activation
4. Success: "Schedule activated. Next wakeup: 2024-06-01 20:37:30"

**Result**: Mothbox will wake every 30 minutes from sunset+30 to sunrise throughout summer, capturing 1,000+ photos for diversity analysis.

### Example 2: Full Moon Observation Session

**Research Goal**: Study moth behavior specifically during full moon periods to measure lunar phobia effect.

**Complete Walkthrough**:

#### Step 1: Plan the Schedule

**Requirements**:
- **Timing**: Full moon ±2 days (5 nights total per lunar cycle)
- **Hours**: Dusk to dawn only (full darkness period)
- **Interval**: Every 15 minutes (higher frequency for behavioral study)
- **Duration**: May-September 2024 (5 full moon cycles)

#### Step 2: Create Schedule

1. Navigate to Scheduler page
2. Click "New Schedule"
3. Name: `Full Moon Observation Session`
4. Description: `Study moth activity and behavior during full moon phases. Captures every 15 minutes from dusk to dawn on full moon ±2 days. Hypothesis: reduced activity during bright moon (lunar phobia).`

#### Step 3: Configure Moon Phase Trigger

1. Select trigger type: **Moon Phase**
2. Select phases: Check only `full`
3. Offset days: `2` (includes 2 days before, day of, 2 days after = 5 nights)
4. Time window:
   - Start: Solar Event → `dusk` → offset `0`
   - End: Solar Event → `dawn` → offset `0`

**Why these settings?**:
- Full moon ±2 days captures peak lunar illumination period
- Dusk to dawn ensures true nighttime observation
- 15-minute interval provides detailed behavioral timeline

#### Step 4: Create Event Pattern

1. Click "Add Event Pattern"
2. Pattern name: `Quick Capture Cycle`
3. Pattern description: `Fast capture cycle for behavioral study - minimal light interference`
4. Add actions:

**Action 1: UV On**
- Type: `gpio`
- Name: `attract_on`
- Offset: `0` minutes
- Description: `Brief UV pulse`

**Action 2: Capture**
- Type: `camera`
- Name: `takephoto`
- Offset: `2` minutes
- Description: `Quick capture`

**Action 3: UV Off**
- Type: `gpio`
- Name: `attract_off`
- Offset: `5` minutes
- Description: `Turn off UV`

5. Save pattern (duration: 5 minutes)

**Why this pattern?**:
- Shorter UV period (5 minutes vs 15) reduces artificial light interference with lunar phobia study
- 2-minute delay allows minimal moth attraction without extended exposure

#### Step 5: Set Date Range

1. Date range:
   - Start: `2024-05-01`
   - End: `2024-09-30`

**Full moon dates in range**:
- May 23, 2024
- June 22, 2024
- July 21, 2024
- August 19, 2024
- September 18, 2024

Each full moon triggers 5 nights of captures (±2 days).

#### Step 6: Preview Results

Click "Preview Schedule":

```
Full Moon Cycles Detected: 5

Cycle 1: May 21-25, 2024 (Full Moon: May 23)
- May 21: 9pm-5:30am, 33 captures
- May 22: 9pm-5:30am, 33 captures
- May 23: 9pm-5:30am, 33 captures (peak)
- May 24: 9pm-5:30am, 33 captures
- May 25: 9pm-5:30am, 33 captures
Subtotal: 165 photos

(Similar for June, July, August, September)

Total: ~825 photos over 25 nights
Average: 33 captures per night
```

#### Step 7: Activate

1. Click "Save Schedule"
2. Click "Activate Schedule"
3. Deployment: Link to existing "Lunar Phobia Study 2024" deployment
4. Confirm activation
5. Next full moon: May 21, 2024 (schedule will begin then)

**Result**: Mothbox activates only during full moon periods, capturing high-frequency data on moth behavior under bright lunar conditions. Compare with new moon data to quantify lunar phobia effect.

### Example 3: Power-Efficient Daily Capture

**Research Goal**: Long-term autonomous deployment in remote location with solar power. Minimize power consumption while maintaining daily presence records.

**Complete Walkthrough**:

#### Step 1: Plan the Schedule

**Requirements**:
- **Power Budget**: Very limited (small solar panel)
- **Goal**: Daily presence/absence data (1 capture per day sufficient)
- **Timing**: Peak activity time (midnight) for best moth diversity
- **Duration**: March-November 2024 (full field season)

**Power Calculation**:
- 1 capture per day: ~10-15 seconds of active time
- Boot + capture + shutdown: ~30 seconds total
- Solar panel can recharge daily with 1 wakeup/day

#### Step 2: Create Schedule

1. Navigate to Scheduler page
2. Click "New Schedule"
3. Name: `Power-Efficient Daily Capture`
4. Description: `Single daily capture at midnight for long-term autonomous monitoring. Optimized for low power consumption in remote solar-powered deployment.`

#### Step 3: Configure Fixed Time Trigger

1. Select trigger type: **Fixed Time**
2. Time: `00:00` (midnight)
3. Days of week: All days selected
4. Date range:
   - Start: `2024-03-01`
   - End: `2024-11-30`

**Why midnight?**:
- Peak moth activity in most species
- Consistent time for seasonal comparison
- Middle of night avoids twilight transition periods

#### Step 4: Create Minimal Event Pattern

1. Click "Add Event Pattern"
2. Pattern name: `Minimal Capture`
3. Pattern description: `Single capture with no lights to conserve power`
4. Add actions:

**Action 1: Capture Only**
- Type: `camera`
- Name: `takephoto`
- Offset: `0` minutes
- Description: `Single capture, no UV lights`
- Parameters: `{}`

5. Save pattern (duration: 0 minutes - immediate execution)

**Why no UV lights?**:
- UV lights draw significant power (~5W for 15 minutes = 75 Wh per night)
- Single capture without lights: ~2W for 30 seconds = 0.017 Wh per night
- 4,400x power reduction
- Passive photography captures moths already present on trap substrate

#### Step 5: Add GPS Sync (Optional)

To ensure accurate timestamps in remote location:

1. Edit pattern
2. Add action:

**Action 0: GPS Sync**
- Type: `gps_sync`
- Name: `gps_sync`
- Offset: `0` minutes
- Description: `Sync time before capture`

**Action 1: Capture**
- Offset: `1` minute (wait for GPS lock)

3. Save pattern (duration: 1 minute)

**Trade-off**: GPS sync adds ~30 seconds of power consumption but ensures accurate timestamps. Skip if time drift is acceptable.

#### Step 6: Preview Results

Click "Preview Schedule":

```
Daily Executions: March 1 - November 30, 2024

2024-03-01 00:00:00 - Capture
2024-03-02 00:00:00 - Capture
2024-03-03 00:00:00 - Capture
...
2024-11-30 00:00:00 - Capture

Total: 275 photos over 275 days
Active time: ~2.3 hours total (30 sec/day × 275 days)
Power consumption: ~4.7 Wh total
```

Compare to full survey:
- 30-minute interval, UV lights: ~2,750 photos, ~200 hours active, ~5,000 Wh
- Daily capture, no lights: ~275 photos, ~2 hours active, ~5 Wh
- **1,000x power reduction** with daily presence data maintained

#### Step 7: Link to Remote Deployment

1. Check "Create new deployment"
2. Deployment name: `Remote Site Alpha - Long Term`
3. Location: (GPS will auto-fill when system wakes)
4. Environmental conditions: `{"power": "solar", "panel_watts": 10, "battery_ah": 20}`
5. Notes: `Autonomous deployment, check quarterly`

#### Step 8: Activate

1. Click "Save Schedule"
2. Click "Activate Schedule"
3. Confirm activation
4. Success: "Schedule activated. Next wakeup: 2024-03-01 00:00:00"

**Result**: Mothbox captures daily presence/absence data with minimal power draw, enabling 9-month autonomous operation on small solar panel. Retrieve SD card quarterly to analyze seasonal patterns.

**Field Deployment Checklist**:
- Test 1 week before deployment to verify wakeups
- Verify RTC battery is fresh (CR2032)
- Confirm solar panel voltage >12V in sunlight
- Check SD card has sufficient space (275 photos ~5-10GB)
- Set up deployment metadata with GPS coordinates

---

## Troubleshooting

### Schedule Not Executing

**Symptom**: Schedule is active, but Mothbox is not waking up or executing actions at scheduled times.

**Checklist**:

1. **Verify schedule is active**
   - Check schedule list for green "Active" badge
   - Only one schedule should be active
   - Action: Re-activate schedule if status is "Inactive"

2. **Check RTC wakealarm is set**
   - SSH to Mothbox
   - Run: `cat /sys/class/rtc/rtc0/wakealarm`
   - Should show Unix timestamp (e.g., `1685577450`)
   - If empty or `0`, wakealarm is not set
   - Action: Re-activate schedule to set RTC

3. **Verify cron jobs are installed**
   - Run: `crontab -l` (list cron jobs for current user)
   - Should show entries from `schedule_settings.csv`
   - Action: Check `CONFIG_DIR/schedule_settings.csv` for correct cron expressions

4. **Check system time is correct**
   - Run: `date`
   - Verify time and timezone are correct
   - Action: Sync with GPS or NTP: `sudo ntpdate -s time.nist.gov`

5. **Review schedule date range**
   - Check if current date is within schedule start/end dates
   - Action: Edit schedule to extend end date if expired

6. **Check battery/power**
   - RTC requires power to wake system
   - Pi 5: Ensure RTC battery (CR2032) is fresh
   - Pi 4: Check PiJuice battery charge
   - Action: Replace battery or charge PiJuice

7. **Review system logs**
   - Check for errors: `journalctl -u mothbox-scheduler -n 50`
   - Look for activation failures or cron errors
   - Action: Address specific errors shown in logs

### Activation Failed

**Symptom**: Click "Activate Schedule" and receive error message. Schedule remains inactive.

**Checklist**:

1. **Validation errors**
   - Check for red error messages in schedule editor
   - Common issues:
     - Missing schedule name
     - No event patterns added
     - Invalid trigger configuration (missing fields)
     - Invalid date range (start after end)
   - Action: Fix validation errors and retry activation

2. **Conflict with active schedule**
   - Error: "Another schedule is currently active"
   - The system requires deactivating the current schedule first
   - Action: Click "Deactivate Active Schedule" in conflict dialog, then retry

3. **RTC permission error**
   - Error: "Failed to set RTC wakealarm: Permission denied"
   - Backend doesn't have permission to write to `/sys/class/rtc/rtc0/wakealarm`
   - Action: Check Flask backend is running as user with RTC permissions (usually requires sudo/root)

4. **Invalid cron expression**
   - Error: "Generated cron expression is invalid"
   - The schedule trigger couldn't be converted to valid cron syntax
   - Action: Simplify trigger configuration, or use Expert Mode to manually enter cron

5. **GPS coordinates missing** (for solar/lunar triggers)
   - Error: "GPS coordinates required for solar trigger"
   - Solar and moon phase triggers need location data
   - Action: Ensure GPS module is connected and obtaining fixes, or manually enter coordinates in deployment metadata

6. **Deployment creation failed**
   - Error: "Failed to create deployment metadata"
   - Selected photo directory doesn't exist or isn't writable
   - Action: Verify photo directory path, check permissions

7. **System busy**
   - Error: "Scheduler service unavailable"
   - Backend service is restarting or under heavy load
   - Action: Wait 30 seconds and retry activation

### Preview Shows No Executions

**Symptom**: Click "Preview Schedule" and the preview shows "No upcoming executions" or empty list.

**Checklist**:

1. **Date range issues**
   - End date is in the past
   - Start date is far in the future
   - Action: Adjust date range to include current date or near-future dates

2. **Time window too restrictive**
   - Example: Interval trigger with window 21:00-22:00 and interval 120 minutes
   - Only 1 execution possible per day (not enough time for second interval)
   - Action: Widen time window or reduce interval

3. **Days of week filter**
   - No days selected in "Days of Week" field
   - Or only 1-2 days selected and preview date range doesn't include those days
   - Action: Select more days of week or adjust preview date range

4. **Moon phase offset too restrictive**
   - Example: Full moon only with offset_days=0
   - Next full moon might be weeks away
   - Action: Increase offset_days to include more nights, or check preview date range extends far enough

5. **Solar event timing**
   - Solar event + offset might be outside 24-hour day
   - Example: sunrise-60min with time window start = sunrise-60 → results in invalid time
   - Action: Adjust offsets to stay within valid time bounds

6. **Cron expression too specific** (Expert Mode)
   - Example: `0 0 31 2 *` (Feb 31 doesn't exist)
   - Invalid day/month combinations
   - Action: Review cron expression for logical errors

7. **Preview date range too short**
   - Default preview shows next 7-14 days
   - If schedule only activates monthly, no executions shown
   - Action: Extend preview date range to 30-90 days

### Wrong Execution Times

**Symptom**: Schedule is executing, but at incorrect times (too early, too late, or wrong days).

**Checklist**:

1. **Timezone mismatch**
   - System timezone doesn't match your location
   - Check: `timedatectl` (should show correct timezone)
   - Action: Set timezone: `sudo timedatectl set-timezone America/New_York` (use your region)

2. **GPS coordinates incorrect** (for solar/lunar)
   - Solar times calculated from wrong location
   - Example: Using default coordinates (0, 0) instead of actual site
   - Action: Verify GPS coordinates in deployment metadata or `controls.txt`

3. **Solar event offset wrong**
   - Check offset sign: +30 (after) vs -30 (before)
   - Example: Wanted sunset+30 but entered sunset-30 (executes before sunset)
   - Action: Edit schedule and correct offset sign

4. **Interval calculation error**
   - Interval trigger may not align to exact times
   - Example: 60-minute interval from 21:00-05:00 → executes at 21:00, 22:00, 23:00, 00:00, etc.
   - If time window start is 21:37 (sunset+30), executions might be 21:37, 22:37, 23:37...
   - This is expected behavior (interval from first trigger time)
   - Action: Use Fixed Time trigger if exact times required

5. **Cron expression not matching intent** (Expert Mode)
   - Check cron fields carefully
   - Example: `0 9-17 * * 1-5` means 9am-5pm weekdays, not 9am and 5pm only
   - Action: Use cron validator tool or test with visual trigger first

6. **Daylight Saving Time (DST)**
   - System clock may not handle DST transitions correctly
   - Schedule times shift by 1 hour during DST change
   - Action: Use solar triggers (auto-adjust) instead of fixed times, or manually edit schedule after DST

7. **Moon phase calculation difference**
   - Different moon phase algorithms may differ by hours
   - System uses local calculation (not online ephemeris)
   - Offset days provide buffer for slight variations
   - Action: Increase offset_days (e.g., ±2 instead of ±1) to ensure coverage

8. **RTC drift**
   - Real-time clock may drift over weeks/months
   - Pi 5 RTC is accurate, but battery backup may fail
   - Pi 4 PiJuice may drift without internet time sync
   - Action: Enable GPS sync action in event patterns to correct time before captures

---

## Best Practices

### For Scientific Surveys

**Naming Conventions**:
- Include year/season in schedule name: "Summer Moth Survey 2024"
- Use descriptive pattern names: "UV Capture Cycle" not "Pattern 1"
- Document intent in descriptions: Why this timing? What species targeted?

**Date Range Management**:
- Always set explicit start/end dates for surveys
- Align with ecological seasons (e.g., June-August for temperate moths)
- Build in buffer days (start May 25 instead of June 1 to catch early emergences)

**GPS Integration**:
- Enable GPS EXIF tagging (see GPS_EXIF_USER_GUIDE.md)
- Link schedule to deployment metadata with coordinates
- Verify GPS lock before field deployment (test 24 hours in lab)

**Data Quality**:
- Add GPS sync action to beginning of event patterns for accurate timestamps
- Use consistent interval throughout survey for temporal comparability
- Document environmental conditions in deployment metadata (temperature, moon phase, weather)

**Replication**:
- Export schedule JSON files for backup and sharing
- Use same schedule across multiple Mothbox units for site replication
- Version control schedule files (e.g., `summer_moth_survey_v2.json`)

**Documentation**:
- Record activation date/time in field notes
- Note any manual intervention (e.g., early deactivation due to weather)
- Link schedule to publications and datasets for reproducibility

### For Power Conservation

**Solar Triggers**:
- Use solar events instead of fixed times to adapt to seasonal changes
- Example: "sunset+30 to sunrise-30" ensures captures during darkness year-round
- Avoids waking during daylight hours (wasted power)

**Consolidated Patterns**:
- Minimize number of wakeups per night
- Example: 1 capture at midnight (1 wakeup) vs 24 captures every 30 minutes (24 wakeups)
- Each wakeup costs ~5-10 Wh (boot overhead), captures cost ~1 Wh each
- Consolidate actions: UV on → photo → UV off (3 actions, 1 wakeup) vs 3 separate wakeups

**Reduce UV Usage**:
- Use shorter UV periods (5-10 minutes instead of 15-30)
- Consider passive photography (no UV) for presence/absence data
- UV lights draw 5-10W continuously (major power drain)

**Interval Optimization**:
- Balance data resolution with power budget
- 60-minute intervals: ~8-10 wakeups/night
- 30-minute intervals: ~16-20 wakeups/night (2x power)
- 15-minute intervals: ~32-40 wakeups/night (4x power)

**Battery Management**:
- Size battery for 3-5 days without sun (cloudy weather buffer)
- Example: 10 wakeups/night × 30 days × 10 Wh/wakeup = 3,000 Wh/month
- Use 100Ah 12V battery (1,200 Wh) with 20W solar panel for safety margin

**Power Monitoring**:
- Enable INA260 power monitor in `controls.txt`
- Track daily power consumption in logs
- Adjust schedule if battery voltage drops below safe threshold

### For Data Quality

**Timing Between Actions**:
- Allow settling time between UV on and photo capture
- Minimum 3-5 minutes for moths to approach and land
- Optimal 5-10 minutes for stable positioning
- Longer periods (10-15 min) improve species diversity in captures

**Action Sequence Logic**:
- GPS sync at start of pattern (offset 0) for accurate timestamps
- UV on before GPS (moths attracted during GPS lock time)
- Photo capture in middle of UV period (moths settled)
- UV off at end (allows moths to depart before next cycle)

**Avoid Rapid Cycling**:
- Don't turn UV on/off too frequently (moths need time to respond)
- Minimum 30-minute intervals for UV cycling
- Consider longer intervals (60-120 min) for behavioral studies

**Photo Settings**:
- Configure camera settings for night photography (high ISO, slow shutter)
- Enable focus bracketing for depth-of-field in macro shots
- Use flash sparingly (disrupts moth behavior)

**Consistency**:
- Use identical schedule settings across survey period
- Avoid changing intervals mid-survey (breaks temporal comparability)
- If adjustments needed, create new schedule version and document change

**Calibration**:
- Run test schedule for 1 week before deployment
- Verify captures occur at expected times
- Check photo quality (exposure, focus, UV illumination)
- Adjust pattern timing based on test results

**Metadata**:
- Link schedule to deployment for context (location, dates, researcher)
- Add custom fields to deployment: `{"survey_type": "biodiversity", "trap_type": "UV sheet"}`
- Export schedule JSON and deployment JSON together for archival

---

## Version History

### v2.0 (December 2024)

**Major Changes**: Visual scheduler UI release (Issues #208-233)

**New Features**:
- Calendar-based schedule creation and management
- Six trigger types: interval, solar, moon phase, fixed time, sensor, cron
- Two-tier architecture: event patterns + schedules
- Expert Mode for raw cron expression editing
- Conflict detection and resolution
- Deployment integration (create/link on activation)
- Schedule import/export/backup
- Real-time preview with execution timeline
- Moon phase calculations (15 solar events, 8 lunar phases)

**Breaking Changes**:
- Replaces CSV-based schedule_settings.csv with JSON schedule files
- Old schedules must be manually migrated (see migration guide)
- New API endpoints (`/api/scheduler/ui/`) separate from legacy cron API

**Components Added**:
- `schedule_schema.py`: Data structures and validation
- `schedule_storage.py`: JSON file I/O
- `cron_bridge.py`: Trigger → cron translation
- `moon_phase.py`, `solar_time.py`: Astronomical calculations
- `scheduler_service.py`: Service layer with caching
- `scheduler_ui.py`: API routes
- Frontend: React components, hooks, context

**Migration Path**:
- Existing CSV schedules continue to work via legacy API
- Visual UI can read CSV and convert to JSON format
- Activate new schedule to transition to JSON-based system

**Documentation**:
- SCHEDULER_USER_GUIDE.md (this document)
- SCHEDULER_DEV_GUIDE.md (developer reference)
- CRON_BRIDGE.md (cron translation reference)

**Testing**:
- 96 unit tests for cron_bridge.py
- 170+ tests for schedule schema and storage
- E2E tests for scheduler UI workflow
- Hardware tests for RTC integration

**Known Issues**:
- Complex cron patterns may not convert to visual triggers
- Moon phase calculations are approximate (±12 hours accuracy)
- RTC set requires root permissions on some systems

**Future Enhancements** (planned for v2.1):
- Power management scheduling (shutdown, sleep modes)
- E-paper display update scheduling
- Multi-schedule queuing (sequential activation)
- Schedule templates and wizards
- Mobile-responsive calendar view
