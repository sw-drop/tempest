
> **Author:** Gary
> **Date:** 2026-07-15  17:
> **Version:** 1.0  
> **Status:** Draft

## Tags: #SFRO-Dash  #Dev


___
# SFRO-Dash v5 Initial Configuration

## Schedule
The day will be set into distinct time periods, specified as UTC:

| Period UTC    | Description                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------- |
| 00:00 - 6:00  | If roof is open, forecast to be open or was open at any time overnight, use: **RoofOpenNight1** |
| 00:00 - 6:00  | If the roof was closed or forecast to be closed all night, use: **RoofClosedNight1**            |
| 06:00 - 9:00  | If roof is open, or was (forecast to be) open at any time overnight, use: **RoofOpenDawn1**     |
| 06:00 - 9:00  | If roof was or was (forecast to be)  closed overnight, use: **RoofClosedDawn1**                 |
| 09:00 - 12:00 | If the roof was (forecast to be) open overnight, use: **RoofOpenMorning1**                      |
| 09:00 - 12:00 | If the roof was (forecast to be) closed overnight, use: **RoofClosedMorning1**                  |
| 12:00-15:00   | If roof is open, or was open at any time overnight, use: **RoofOpenLunch1**                     |
| 12:00-15:00   | If the roof was closed all night, use: **RoofClosedLunch1**                                     |
| 15:00 - 18:00 | Use: **Afternoon1** schema                                                                      |
| 18:00 - 21:00 | Use: **Supper1** schema                                                                         |
| 21:00 - 23:59 | If roof is forecast to open at any time in the night, use: **RoofOpenEvening1**                 |
| 21:00 - 23:59 | If roof is forecast to NOT open at any time in the night, use: **RoofClosedEvening1**           |

Note that there needs to be some logic to define if the roof is/was open or closed (or is forecast to be open.)

---
# Schema Outlines

## RoofOpenNight1 Schema 00:00 - 6:00

In this scenario, there is some prospect of the roof opening per the yr.no forecast for Starfront. In mid winter, it is possible that the roof is already open or will open within the next hour.

**forecast-card** 
Should show Starfront forecast starting at the hour before sunset or the current time if later.

In this schema, the **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.

**Image cards**
The sky cam card should be left as default. 

If any images were captured, as seen in the Discord feed, the last fits image for each scope (converted to jpeg) should be displayed if it has arrived in the input directory (the default behaviour.) 

If there are no images or the first one hasn't arrived yet, show "Pending first image" in the title bar and show the "Observatory Forecast" script output text in the 75Q card and the "Astrospheric Forecast" image copied from the sfro-dashboard at http://192.168.1.60:8081 in the FRA400 card.

**Capture cards**
The capture cards should show the forecast for each scope until the first image is captured, and then they should add the real-time capture totals using the existing script (adapted if needs be). If the actual capture matches the forecast capture, show the progress (like the forecast might have said "Target Name 45" and then when the first image arrives, show "Target name 1 of 45") and keep it updated.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data.
The yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. The text from the http://192.168.1.60:8081 dashboard that follows the pattern:
**Roof Open:** 15m before sunset, Anticipated: 02:28 BST (Sunset: 02:43 BST)
**Roof Close:** 5m after sunrise, Anticipated: 12:48 BST (Sunrise: 12:43 BST)

When the observatory forecast for the night arrives, that should be shown instead of the yr forecast, minus the "Tomorrow's outlook:" line if that exists. The time of the message (in central time) should be shown.

**Atmos cards**
Default: The **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.


---
## RoofClosedNight1 Schema 00:00 - 6:00

In this scenario, there is very little prospect of the roof opening per the yr.no forecast for Starfront. 

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
The output of "Observatory Forecast" script.
The output of "Night Sky Flower Monitor" script if there was any, and only if the period indicated is during or after the current time.

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data. If there was no Discord roof message in the last 18 hours, Just show "Closed".
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 


**Atmos cards**
In this schema, the **atmos-left-card** / **atmos-right-card** should be Wandsworth (left) and Umhlanga.

---
## RoofOpenDawn1 Schema 06:00 - 9:00
In this schema, the roof has opened, is open or is expected to open.

**forecast-card** 
Should show Starfront forecast starting at the hour before sunset or the current time if later.

**Image cards**
The sky cam card should be left as default. 

If any images were captured, as seen in the Discord feed, the last fits image for each scope (converted to jpeg) should be displayed if it has arrived in the input directory (the default behaviour.) 

If there are no images or the first one hasn't arrived yet, show "Pending first image" in the title bar and show the "Observatory Forecast" script output text in the 75Q card and the "Astrospheric Forecast" image copied from the sfro-dashboard at http://192.168.1.60:8081 in the FRA400 card.

**Capture cards**
The capture cards should show the forecast for each scope until the first image is captured, and then they should add the real-time capture totals using the existing script (adapted if needs be). If the actual capture matches the forecast capture, show the progress (like the forecast might have said "Target Name 45" and then when the first image arrives, show "Target name 1 of 45") and keep it updated.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data.
The yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. The text from the http://192.168.1.60:8081 dashboard that follows the pattern:
**Roof Open:** 15m before sunset, Anticipated: 02:28 BST (Sunset: 02:43 BST)
**Roof Close:** 5m after sunrise, Anticipated: 12:48 BST (Sunrise: 12:43 BST)

When the observatory forecast for the night arrives, that should be shown instead of the yr forecast, minus the "Tomorrow's outlook:" line if that exists. The time of the message (in central time) should be shown.

**Atmos cards**
Default: The **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.


---
## RoofClosedDawn1 Schema 06:00 - 9:00

In this scenario, there is very little prospect of the roof opening per the yr.no forecast for Starfront. 

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data. If there was no Discord roof message in the last 18 hours, Just show "Closed".
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 

**Atmos cards**
In this schema, the **atmos-left-card** / **atmos-right-card** should be Wandsworth (left) and Umhlanga.

---

## RoofOpenMorning1 Schema 09:00 - 12:00
In this schema, the roof has opened, is open or is expected to open.

**forecast-card** 
Should show Starfront forecast starting at the hour before sunset or the current time if later.

**Image cards**
The sky cam card should be left as default. 

If any images were captured, as seen in the Discord feed, the last fits image for each scope (converted to jpeg) should be displayed if it has arrived in the input directory (the default behaviour.) 

If there are no images or the first one hasn't arrived yet, show "Pending first image" in the title bar and show the "Observatory Forecast" script output text in the 75Q card and the "Astrospheric Forecast" image copied from the sfro-dashboard at http://192.168.1.60:8081 in the FRA400 card.

**Capture cards**
The capture cards should show the forecast for each scope until the first image is captured, and then they should add the real-time capture totals using the existing script (adapted if needs be). If the actual capture matches the forecast capture, show the progress (like the forecast might have said "Target Name 45" and then when the first image arrives, show "Target name 1 of 45") and keep it updated.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data.
The Starfront yr.no forecast up until dawn interpreted as a few words of text with a focus on the likelihood of clear sky conditions and the prospect of the roof opening. 
The text from the http://192.168.1.60:8081 dashboard that follows the pattern:
**Roof Close:** 5m after sunrise, Anticipated: 12:48 BST (Sunrise: 12:43 BST)

When the observatory forecast for the night arrives, that should be shown instead of the yr forecast, minus the "Tomorrow's outlook:" line if that exists. The time of the message (in central time) should be shown.

**Atmos cards**
Default: The **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.


---
## RoofClosedMorning1 Schema 09:00 - 12:00
In this scenario, there is very little prospect of the roof opening per the yr.no forecast for Starfront. 

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data. If there was no Discord roof message in the last 18 hours, Just show "Closed".
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 

**Atmos cards**
In this schema, the **atmos-left-card** / **atmos-right-card** should be Wandsworth (left) and Umhlanga.

---

## RoofOpenLunch1 12:00-15:00
In this schema, the roof has opened, is open or is expected to open.

**forecast-card** 
Should show London forecast starting at the hour before sunset or the current time if later.

**Image cards**
The sky cam card should be left as default. 

If any images were captured, as seen in the Discord feed, the last fits image for each scope (converted to jpeg) should be displayed if it has arrived in the input directory (the default behaviour.) 

If there are no images or the first one hasn't arrived yet, show "Pending first image" in the title bar and show the "Observatory Forecast" script output text in the 75Q card and the "Astrospheric Forecast" image copied from the sfro-dashboard at http://192.168.1.60:8081 in the FRA400 card.

**Capture cards**
The capture cards should show the forecast for each scope until the first image is captured, and then they should add the real-time capture totals using the existing script (adapted if needs be). If the actual capture matches the forecast capture, show the progress (like the forecast might have said "Target Name 45" and then when the first image arrives, show "Target name 1 of 45") and keep it updated.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data.
Alert if either scope has any wait state forecast for the coming/next night, regardless of roof opening forecast.
The Starfront yr.no forecast up until dawn interpreted as a few words of text with a focus on the likelihood of clear sky conditions and the prospect of the roof opening. 
The text from the http://192.168.1.60:8081 dashboard that follows the pattern:
**Roof Open:** - Do not show
**Roof Close:** 5m after sunrise, Anticipated: 12:48 BST (Sunrise: 12:43 BST)

When the observatory forecast for the night arrives, that should be shown instead of the yr forecast, minus the "Tomorrow's outlook:" line if that exists. The time of the message (in central time) should be shown.

**Atmos cards**
Default: The **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.

---
## RoofClosedLunch1 12:00-15:00
In this scenario, there is very little prospect of the roof opening per the yr.no forecast for Starfront. 

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
Alert if either scope has any wait state forecast for the coming/next night, regardless of roof opening forecast.
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data. If there was no Discord roof message in the last 18 hours, Just show "Closed".
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 


**Atmos cards**
In this schema, the **atmos-left-card** / **atmos-right-card** should be Wandsworth (left) and Umhlanga.




---
## Afternoon1** 15:00 - 18:00

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
Alert if either scope has any wait state forecast for the coming/next night, regardless of roof opening forecast.
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 


---
## Supper1 18:00 - 21:00

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should show the the NASA APOD image.
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show ./images/NightB.jpg

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
Alert if either scope has any wait state forecast for the coming/next night, regardless of roof opening forecast.
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 

---
## RoofOpenEvening1 21:00 - 23:59
In this scenario, there is some prospect of the roof opening per the yr.no forecast for Starfront. In mid winter, it is possible that the roof is already open or will open within the next hour.

**forecast-card** 
Should show Starfront forecast starting at the hour before sunset or the current time if later.

In this schema, the **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.

**Image cards**
The sky cam card should be left as default. 

If any images were captured, as seen in the Discord feed, the last fits image for each scope (converted to jpeg) should be displayed if it has arrived in the input directory (the default behaviour.) 

The 75Q card should show NightA.jpg and the FRA400 card should show NightB.jpg

**Capture cards**
The capture cards should show the forecast for each scope until the first image is captured, and then they should add the real-time capture totals using the existing script (adapted if needs be). If the actual capture matches the forecast capture, show the progress (like the forecast might have said "Target Name 45" and then when the first image arrives, show "Target name 1 of 45") and keep it updated.

**The roofbox card should show:**
The roof state (open/closed) in the title and the time of the update. This is based on the Discord feed data.
The yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. The text from the http://192.168.1.60:8081 dashboard that follows the pattern:
**Roof Open:** 15m before sunset, Anticipated: 02:28 BST (Sunset: 02:43 BST)


**Atmos cards**
Default: The **atmos-left-card** / **atmos-right-card** should be left at default of Starfront and Umhlanga.

---

## RoofClosedEvening1 21:00 - 23:59
This card is used if the expectation is that the roof will not open based on the yr.no forecast.

**forecast-card** 
Should show Wandsworth forecast starting at the current hour.

**Image cards**
The sky cam card should be left as default. 
The **q75img-card** should be switched to text and show:
A textual summarisation of the output from "Daily Backup Volume Report"
A textual summarisation of the output from "Daily Container Backup Report" (not in place as of 15Jul202)

The **fra400img-card** should show the the NASA APOD image.

**Capture cards**
Should be switched to showing the currency cards.

**The roofbox card should show:**
Alert if either scope has any wait state forecast for the coming/next night, regardless of roof opening forecast.
The Starfront yr.no forecast interpreted as a few words of text with a focus on the liklihood of clear sky conditions and the prospect of the roof opening. 


---
# Dashboard Card Layout Map

Here is a visual map of how the cards are positioned on the 12×12 screen grid:

| Column 1 (Left Area)                                                                                                        | Column 2 (Middle Area)                                                  | Column 3 (Right Area)                                                                    |
| :-------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- | :--------------------------------------------------------------------------------------- |
| **skycam-card**<br>*(Live All-Sky Camera)*<br>Grid: Cols 1-4, Rows 1-7                                                      | **fra400img-card**<br>*(FRA400 Image/Text)*<br>Grid: Cols 5-8, Rows 1-6 | **forecast-card**<br>*(Forecast & Status)*<br>Grid: Cols 9-12, Rows 1-4                  |
| **skycam-card** *(continued)*                                                                                               | **fra400img-card** *(continued)*                                        | **fra400cap-card** / **q75cap-card**<br>*(Capture Reports)*<br>Grid: Cols 9-12, Rows 5-7 |
| **atmos-left-card** / **atmos-right-card**<br>*(Left & Right Atmospheric Columns)*<br>Grid: Cols 1-4 (split 2+2), Rows 8-12 | **q75img-card**<br>*(75Q Image/Text)*<br>Grid: Cols 5-8, Rows 7-12      | **roofbox-card**<br>*(Roof Status log)*<br>Grid: Cols 9-12, Rows 8-11                    |
| **atmos-left-card** / **atmos-right-card** *(continued)*                                                                    | **q75img-card** *(continued)*                                           | **uktime-card** / **ustime-card**<br>*(BST & Central Clocks)*<br>Grid: Cols 9-12, Row 12 |


---
## Reference list of every card:
The cards bottom left have changed since this was written!

| Screen Position & Content | Current CSS Class | Proposed Programmatic ID | Grid Layout Details |
| :--- | :--- | :--- | :--- |
| **Top Left**: Live All-Sky Camera feed | `.skycam` | `skycam-card` | Cols 1-4, Rows 1-7 |
| **Top Middle**: FRA400 Image (or text) | `.fra400img` | `fra400img-card` | Cols 5-8, Rows 1-6 |
| **Bottom Middle**: 75Q Image (or text) | `.q75img` | `q75img-card` | Cols 5-8, Rows 7-12 |
| **Bottom Left**: Atmospheric weather telemetry | `.atmos` | `atmos-card` | Cols 1-4, Rows 8-12 |
| **Middle Right (Left)**: FRA400 Capture text | `.fra400cap` | `fra400cap-card` | Cols 9-10, Rows 5-7 |
| **Middle Right (Right)**: 75Q Capture text | `.q75cap` | `q75cap-card` | Cols 11-12, Rows 5-7 |
| **Top Right**: Roof Status Header & Forecast timeline | `.forecast` | `forecast-card` | Cols 9-12, Rows 1-4 |
| **Bottom Right (Top)**: Roof Status log/events | `.roofbox` | `roofbox-card` | Cols 9-12, Rows 8-11 |
| **Bottom Right (Clock Left)**: Local Time (UK) | `.uktime` | `uktime-card` | Cols 9-10, Row 12 |
| **Bottom Right (Clock Right)**: US Central Time | `.ustime` | `ustime-card` | Cols 11-12, Row 12 |



___
## References


___
